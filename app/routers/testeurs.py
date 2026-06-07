from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.testeur import Testeur
from app.models.habilitation_testeur import HabilitationTesteur
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter(prefix="/api/testeurs", tags=["Testeurs"])

class TesteurCreate(BaseModel):
    nom: str
    prenom: str
    statut: str = "interne"
    etat: str = "actif"
    entreprise: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    numero_inrs: Optional[str] = None
    date_habilitation: Optional[date] = None
    date_expiration_habilitation: Optional[date] = None
    visite_medicale: Optional[date] = None
    visite_medicale_date: Optional[date] = None
    evaluation_date: Optional[date] = None
    formation_continue: Optional[date] = None
    date_prochain_controle: Optional[date] = None
    note: Optional[str] = None

class TesteurResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    statut: str
    entreprise: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    numero_inrs: Optional[str] = None
    date_habilitation: Optional[date] = None
    date_expiration_habilitation: Optional[date] = None
    visite_medicale: Optional[date] = None
    formation_continue: Optional[date] = None
    date_prochain_controle: Optional[date] = None
    note: Optional[str] = None
    actif: bool

    class Config:
        from_attributes = True

@router.get("/", response_model=list[TesteurResponse])
def liste_testeurs(db: Session = Depends(get_db)):
    return db.query(Testeur).filter(Testeur.actif == True).all()

@router.get("/{id}", response_model=TesteurResponse)
def get_testeur(id: int, db: Session = Depends(get_db)):
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    return t

@router.post("/", response_model=TesteurResponse)
def create_testeur(data: TesteurCreate, db: Session = Depends(get_db)):
    t = Testeur(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@router.put("/{id}", response_model=TesteurResponse)
def update_testeur(id: int, data: TesteurCreate, db: Session = Depends(get_db)):
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    for key, value in data.model_dump(exclude={'etat'}).items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return t

@router.put("/{id}/etat")
def update_etat_testeur(id: int, pin: str, etat: str, db: Session = Depends(get_db)):
    if pin != "1505":
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    if etat not in ("actif", "suspendu", "sorti"):
        raise HTTPException(status_code=400, detail="État invalide")
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    t.etat = etat
    db.commit()
    return {"message": "État mis à jour"}

@router.delete("/{id}")
def delete_testeur(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    t.actif = False
    db.commit()
    return {"message": "Testeur archive"}