from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.stagiaire import Stagiaire
from pydantic import BaseModel
from datetime import date
from typing import Optional
import shutil
import os

router = APIRouter(prefix="/stagiaires", tags=["Stagiaires"])

UPLOAD_DIR = "uploads/photos"

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
    return db.query(Stagiaire).filter(Stagiaire.actif == 1).order_by(Stagiaire.nom, Stagiaire.prenom).all()

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

@router.post("/photo/{id}")
def upload_photo(id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Format non supporte")
    filename = f"stagiaire_{id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    s.photo = f"/uploads/photos/{filename}"
    db.commit()
    return {"message": "Photo uploadee", "photo": s.photo}

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