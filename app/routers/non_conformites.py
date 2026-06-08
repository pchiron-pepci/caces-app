import base64
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.non_conformite import NonConformite
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter(prefix="/api/non-conformites", tags=["Non-conformités"])


class NonConformiteCreate(BaseModel):
    date: date
    declarant_id: Optional[int] = None
    origine: str
    type_nc: str
    nature: Optional[str] = None
    titre: str
    description: Optional[str] = None
    action_preventive: Optional[str] = None
    action_corrective: Optional[str] = None
    justificatif_pdf: Optional[str] = None
    justificatif_nom: Optional[str] = None
    statut: str = "ouvert"
    session_id: Optional[int] = None
    testeur_id: Optional[int] = None
    stagiaire_id: Optional[int] = None


class NonConformiteUpdate(BaseModel):
    date: date
    declarant_id: Optional[int] = None
    origine: str
    type_nc: str
    nature: Optional[str] = None
    titre: str
    description: Optional[str] = None
    action_preventive: Optional[str] = None
    action_corrective: Optional[str] = None
    justificatif_pdf: Optional[str] = None
    justificatif_nom: Optional[str] = None
    statut: Optional[str] = None
    session_id: Optional[int] = None
    testeur_id: Optional[int] = None
    stagiaire_id: Optional[int] = None


def _generate_reference(db: Session, year: int) -> str:
    prefix = f"NC-{year}-"
    last = db.query(NonConformite).filter(
        NonConformite.reference.like(f"{prefix}%")
    ).order_by(NonConformite.reference.desc()).first()
    if last and last.reference:
        try:
            n = int(last.reference.rsplit("-", 1)[-1]) + 1
        except ValueError:
            n = 1
    else:
        n = 1
    return f"{prefix}{n:03d}"


@router.post("")
def create_nc(data: NonConformiteCreate, db: Session = Depends(get_db)):
    nc = NonConformite(**data.model_dump())
    nc.reference = _generate_reference(db, data.date.year)
    db.add(nc)
    db.commit()
    db.refresh(nc)
    return {"message": "Non-conformité créée", "id": nc.id, "reference": nc.reference}


@router.put("/{id}")
def update_nc(id: int, data: NonConformiteUpdate, db: Session = Depends(get_db)):
    nc = db.query(NonConformite).filter(NonConformite.id == id).first()
    if not nc:
        raise HTTPException(status_code=404, detail="Non-conformité non trouvée")
    if nc.statut in ("cloture", "sans_objet"):
        raise HTTPException(status_code=403, detail="Une non-conformité clôturée ou classée sans objet ne peut pas être modifiée. Rouvrez-la d'abord.")
    update_data = data.model_dump(exclude_none=True, exclude={"statut"})
    for key, value in update_data.items():
        setattr(nc, key, value)
    if data.statut in ("ouvert", "en_cours"):
        nc.statut = data.statut
    db.commit()
    return {"message": "Non-conformité mise à jour"}


@router.patch("/{id}/cloturer")
def cloturer_nc(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    nc = db.query(NonConformite).filter(NonConformite.id == id).first()
    if not nc:
        raise HTTPException(status_code=404, detail="Non-conformité non trouvée")
    nc.statut = "cloture"
    nc.date_cloture = date.today()
    db.commit()
    return {"message": "Non-conformité clôturée"}


@router.patch("/{id}/rouvrir")
def rouvrir_nc(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    nc = db.query(NonConformite).filter(NonConformite.id == id).first()
    if not nc:
        raise HTTPException(status_code=404, detail="Non-conformité non trouvée")
    nc.statut = "ouvert"
    nc.date_cloture = None
    db.commit()
    return {"message": "Non-conformité réouverte"}


@router.patch("/{id}/sans-objet")
def sans_objet_nc(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    nc = db.query(NonConformite).filter(NonConformite.id == id).first()
    if not nc:
        raise HTTPException(status_code=404, detail="Non-conformité non trouvée")
    nc.statut = "sans_objet"
    nc.date_cloture = date.today()
    db.commit()
    return {"message": "Non-conformité classée sans objet"}


@router.get("/{id}/justificatif")
def download_justificatif(id: int, db: Session = Depends(get_db)):
    nc = db.query(NonConformite).filter(NonConformite.id == id).first()
    if not nc or not nc.justificatif_pdf:
        raise HTTPException(status_code=404, detail="Justificatif non disponible")
    pdf_bytes = base64.b64decode(nc.justificatif_pdf)
    filename = nc.justificatif_nom or f"justificatif_{id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )
