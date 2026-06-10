from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models.attestation_neutralite import AttestationNeutralite

router = APIRouter(prefix="/api/neutralite", tags=["Neutralite"])


class VerificationCreate(BaseModel):
    verificateur_identite: str


class AttestationCreate(BaseModel):
    signature_base64: str


@router.get("/jour/{jour_test_id}/statuts")
def get_statuts(jour_test_id: int, db: DBSession = Depends(get_db)):
    attestations = db.query(AttestationNeutralite).filter(
        AttestationNeutralite.jour_test_id == jour_test_id
    ).all()
    return {
        a.stagiaire_id: ("signe" if a.horodatage is not None else "en_attente")
        for a in attestations
    }


@router.post("/{jour_test_id}/{stagiaire_id}/verification")
async def enregistrer_verification(
    jour_test_id: int,
    stagiaire_id: int,
    data: VerificationCreate,
    db: DBSession = Depends(get_db)
):
    now = datetime.utcnow()
    existing = db.query(AttestationNeutralite).filter(
        AttestationNeutralite.jour_test_id == jour_test_id,
        AttestationNeutralite.stagiaire_id == stagiaire_id
    ).first()
    if existing:
        existing.verificateur_identite = data.verificateur_identite
        existing.horodatage_verification = now
    else:
        db.add(AttestationNeutralite(
            jour_test_id=jour_test_id,
            stagiaire_id=stagiaire_id,
            verificateur_identite=data.verificateur_identite,
            horodatage_verification=now
        ))
    db.commit()
    return {"ok": True}


@router.post("/{jour_test_id}/{stagiaire_id}")
async def upsert_attestation(
    jour_test_id: int,
    stagiaire_id: int,
    data: AttestationCreate,
    request: Request,
    db: DBSession = Depends(get_db)
):
    ip = request.client.host if request.client else None
    now = datetime.utcnow()
    existing = db.query(AttestationNeutralite).filter(
        AttestationNeutralite.jour_test_id == jour_test_id,
        AttestationNeutralite.stagiaire_id == stagiaire_id
    ).first()
    if existing:
        existing.signature_base64 = data.signature_base64
        existing.horodatage = now
        existing.ip_address = ip
    else:
        db.add(AttestationNeutralite(
            jour_test_id=jour_test_id,
            stagiaire_id=stagiaire_id,
            signature_base64=data.signature_base64,
            horodatage=now,
            ip_address=ip
        ))
    db.commit()
    return {"ok": True}
