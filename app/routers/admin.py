from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.categorie import Categorie, Famille
from app.models.habilitation_testeur import HabilitationTesteur
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/admin", tags=["Administration"])

class HabilitationCreate(BaseModel):
    testeur_id: int
    famille: str
    categorie: str
    date_integration: date
    option_pe: bool = False
    option_tel: bool = False

@router.get("/categories/{famille}")
def get_categories_famille(famille: str, db: Session = Depends(get_db)):
    f = db.query(Famille).filter(Famille.code == famille).first()
    if not f:
        raise HTTPException(status_code=404, detail="Famille non trouvee")
    cats = db.query(Categorie).filter(
        Categorie.famille_id == f.id,
        Categorie.actif == True
    ).all()
    return [{"code": c.code, "libelle": c.libelle} for c in cats]

@router.post("/categorie/{id}/activer")
def activer_categorie(id: int, db: Session = Depends(get_db)):
    c = db.query(Categorie).filter(Categorie.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    c.pepci_habilite = True
    db.commit()
    return {"message": "Categorie activee"}

@router.post("/categorie/{id}/desactiver")
def desactiver_categorie(id: int, db: Session = Depends(get_db)):
    c = db.query(Categorie).filter(Categorie.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    c.pepci_habilite = False
    db.commit()
    return {"message": "Categorie desactivee"}

@router.post("/habilitation")
def add_habilitation(data: HabilitationCreate, db: Session = Depends(get_db)):
    h = HabilitationTesteur(**data.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"message": "Habilitation ajoutee", "id": h.id}

@router.delete("/habilitation/{id}")
def delete_habilitation(id: int, db: Session = Depends(get_db)):
    h = db.query(HabilitationTesteur).filter(HabilitationTesteur.id == id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habilitation non trouvee")
    h.actif = False
    db.commit()
    return {"message": "Habilitation retiree"}