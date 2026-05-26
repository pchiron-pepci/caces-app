from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.stagiaire import Stagiaire
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter(prefix="/stagiaires", tags=["Stagiaires"])

class StagiaireCreate(BaseModel):
    nom: str
    prenom: str
    date_naissance: date
    email: Optional[str] = None
    telephone: Optional[str] = None
    employeur: Optional[str] = None
    note: Optional[str] = None

class StagiaireResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    date_naissance: date
    email: Optional[str] = None
    telephone: Optional[str] = None
    employeur: Optional[str] = None
    note: Optional[str] = None
    photo: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=list[StagiaireResponse])
def liste_stagiaires(db: Session = Depends(get_db)):
    return db.query(Stagiaire).filter(Stagiaire.actif == 1).all()

@router.get("/{id}", response_model=StagiaireResponse)
def get_stagiaire(id: int, db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    return s

@router.post("/", response_model=StagiaireResponse)
def create_stagiaire(data: StagiaireCreate, db: Session = Depends(get_db)):
    s = Stagiaire(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.put("/{id}", response_model=StagiaireResponse)
def update_stagiaire(id: int, data: StagiaireCreate, db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    for key, value in data.model_dump().items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/{id}")
def delete_stagiaire(id: int, pin: str, db: Session = Depends(get_db)):
    PIN_SECRET = "1505"
    if pin != PIN_SECRET:
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    s.actif = 0
    db.commit()
    return {"message": "Stagiaire archive"}