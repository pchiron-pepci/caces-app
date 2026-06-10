from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.consentement_rgpd import ConsentementRGPD
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/consentements", tags=["Consentements"])


class VerificationCreate(BaseModel):
    verificateur_identite: str


class ConsentementCreate(BaseModel):
    rgpd_accepte: bool
    photo_accepte: bool
    plaintes_atteste: bool
    signature_base64: str


@router.get("/session/{session_id}/statuts")
def get_statuts(session_id: int, db: DBSession = Depends(get_db)):
    consentements = db.query(ConsentementRGPD).filter(
        ConsentementRGPD.session_id == session_id
    ).all()
    result = {}
    for c in consentements:
        if c.horodatage is not None:
            if c.rgpd_accepte and c.photo_accepte and c.plaintes_atteste:
                statut = "traite_tout"
            else:
                statut = "traite_refus"
        else:
            statut = "en_attente"
        result[c.stagiaire_id] = statut
    return result


@router.post("/{session_id}/{stagiaire_id}/verification")
async def enregistrer_verification(
    session_id: int,
    stagiaire_id: int,
    data: VerificationCreate,
    db: DBSession = Depends(get_db)
):
    now = datetime.utcnow()
    existing = db.query(ConsentementRGPD).filter(
        ConsentementRGPD.session_id == session_id,
        ConsentementRGPD.stagiaire_id == stagiaire_id
    ).first()
    if existing:
        existing.verificateur_identite = data.verificateur_identite
        existing.horodatage_verification = now
    else:
        c = ConsentementRGPD(
            session_id=session_id,
            stagiaire_id=stagiaire_id,
            verificateur_identite=data.verificateur_identite,
            horodatage_verification=now
        )
        db.add(c)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/{stagiaire_id}")
async def upsert_consentement(
    session_id: int,
    stagiaire_id: int,
    data: ConsentementCreate,
    request: Request,
    db: DBSession = Depends(get_db)
):
    ip = request.client.host if request.client else None
    now = datetime.utcnow()

    existing = db.query(ConsentementRGPD).filter(
        ConsentementRGPD.session_id == session_id,
        ConsentementRGPD.stagiaire_id == stagiaire_id
    ).first()

    if existing:
        # Mise à jour uniquement des champs signature — ne pas écraser la vérification
        existing.rgpd_accepte = data.rgpd_accepte
        existing.photo_accepte = data.photo_accepte
        existing.plaintes_atteste = data.plaintes_atteste
        existing.signature_base64 = data.signature_base64
        existing.horodatage = now
        existing.ip_address = ip
    else:
        c = ConsentementRGPD(
            session_id=session_id,
            stagiaire_id=stagiaire_id,
            rgpd_accepte=data.rgpd_accepte,
            photo_accepte=data.photo_accepte,
            plaintes_atteste=data.plaintes_atteste,
            signature_base64=data.signature_base64,
            horodatage=now,
            ip_address=ip
        )
        db.add(c)

    db.commit()
    return {"ok": True}
