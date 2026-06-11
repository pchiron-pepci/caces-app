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
    import base64 as _b64
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouve")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Format non supporte")
    raw = file.file.read()
    s.photo_base64 = _b64.b64encode(raw).decode()
    s.photo = f"/uploads/photos/stagiaire_{id}{ext}"
    db.commit()
    return {"message": "Photo uploadee", "photo_base64": True}

class PhotoBase64Payload(BaseModel):
    photo_base64: str

@router.post("/{id}/photo-upload")
def upload_photo_base64(id: int, payload: PhotoBase64Payload, db: Session = Depends(get_db)):
    import base64 as _b64
    from io import BytesIO
    from PIL import Image
    s = db.query(Stagiaire).filter(Stagiaire.id == id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire non trouvé")
    b64_str = payload.photo_base64
    if ',' in b64_str:
        b64_str = b64_str.split(',', 1)[1]
    try:
        raw = _b64.b64decode(b64_str)
        img = Image.open(BytesIO(raw)).convert('RGB')
        w, h = img.size
        if max(w, h) > 600:
            ratio = 600 / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=80)
        final_b64 = _b64.b64encode(buf.getvalue()).decode()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Image invalide : {exc}")
    s.photo_base64 = final_b64
    s.photo = f"/uploads/photos/stagiaire_{id}.jpg"
    db.commit()
    return {"ok": True}

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

@router.get("/{id}/historique")
def get_historique_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.session_candidat import SessionCandidat
    from app.models.session import Session as SessionModel
    from app.models.jour_test import JourTest, JourTestCandidat, ResultatTheorie
    from app.models.session_epreuve import SessionEpreuve

    candidats = db.query(SessionCandidat).filter(
        SessionCandidat.stagiaire_id == id,
        SessionCandidat.actif == True
    ).all()

    result = []
    for sc in candidats:
        session = db.query(SessionModel).filter(SessionModel.id == sc.session_id).first()
        if not session:
            continue

        theorie_results = db.query(ResultatTheorie).filter(
            ResultatTheorie.session_id == sc.session_id,
            ResultatTheorie.stagiaire_id == id
        ).all()

        theorie = None
        if theorie_results:
            obtenu_list = [r for r in theorie_results if r.obtenue == True]
            if obtenu_list:
                best = max(obtenu_list, key=lambda r: r.id)
                theorie = {"statut": "obtenu", "note": round(best.note_totale) if best.note_totale is not None else None}
            else:
                non_obtenu = [r for r in theorie_results if r.obtenue == False]
                if non_obtenu:
                    recent = max(non_obtenu, key=lambda r: r.id)
                    theorie = {"statut": "non_obtenu", "note": round(recent.note_totale) if recent.note_totale is not None else None}
                else:
                    theorie = {"statut": "planifie", "note": None}
        else:
            theorie_jours = db.query(JourTest).filter(
                JourTest.session_id == sc.session_id,
                JourTest.type == 'theorie',
                JourTest.actif == True
            ).all()
            for tj in theorie_jours:
                jtc = db.query(JourTestCandidat).filter(
                    JourTestCandidat.jour_test_id == tj.id,
                    JourTestCandidat.stagiaire_id == id
                ).first()
                if jtc:
                    theorie = {"statut": "planifie", "note": None}
                    break

        epreuves = db.query(SessionEpreuve).filter(
            SessionEpreuve.session_id == sc.session_id,
            SessionEpreuve.stagiaire_id == id
        ).all()

        pratique_jours = db.query(JourTest).filter(
            JourTest.session_id == sc.session_id,
            JourTest.type == 'pratique',
            JourTest.actif == True
        ).all()

        planned_cats = set()
        for j in pratique_jours:
            jtcs = db.query(JourTestCandidat).filter(
                JourTestCandidat.jour_test_id == j.id,
                JourTestCandidat.stagiaire_id == id
            ).all()
            for jtc in jtcs:
                for cat in (jtc.categories or '').split(','):
                    cat = cat.strip()
                    if cat:
                        planned_cats.add(cat)

        evaluated_cats = {e.categorie for e in epreuves}
        pratique = []
        for e in epreuves:
            if e.obtenue == True:
                statut = "obtenu"
            elif e.obtenue == False:
                statut = "non_obtenu"
            else:
                statut = "planifie"
            pratique.append({
                "categorie": e.categorie,
                "statut": statut,
                "options": e.options_obtenues or ""
            })
        for cat in sorted(planned_cats - evaluated_cats):
            pratique.append({"categorie": cat, "statut": "planifie", "options": ""})

        result.append({
            "session_id": session.id,
            "reference": session.reference or f"Session #{session.id}",
            "famille": session.famille,
            "date_theorie": session.date_theorie.isoformat() if session.date_theorie else None,
            "date_pratique_debut": session.date_pratique_debut.isoformat() if session.date_pratique_debut else None,
            "date_pratique_fin": session.date_pratique_fin.isoformat() if session.date_pratique_fin else None,
            "statut": session.statut,
            "theorie": theorie,
            "pratique": pratique,
        })

    result.sort(key=lambda x: x["session_id"], reverse=True)
    return result


@router.get("/{id}/cartes-emises")
def get_cartes_emises_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.carte_caces import CarteCaces
    cartes = (
        db.query(CarteCaces)
        .filter(CarteCaces.stagiaire_id == id, CarteCaces.statut.in_(["emise", "remplacee"]))
        .order_by(CarteCaces.date_generation.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "numero_carte": c.numero_carte,
            "famille": c.famille,
            "date_generation": c.date_generation.isoformat() if c.date_generation else None,
            "statut": c.statut,
        }
        for c in cartes
    ]


@router.get("/{id}/caces-valides")
def get_caces_valides_stagiaire(id: int, db: Session = Depends(get_db)):
    from app.models.caces_obtenu import CacesObtenu
    from app.models.session_epreuve import SessionEpreuve
    from app.models.testeur import Testeur

    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == id, CacesObtenu.statut == "valide")
        .order_by(CacesObtenu.numero_ordre.desc())
        .all()
    )

    result = []
    for co in cos:
        ep = db.query(SessionEpreuve).filter(
            SessionEpreuve.stagiaire_id == id,
            SessionEpreuve.session_id == co.session_id,
            SessionEpreuve.categorie == co.categorie,
            SessionEpreuve.obtenue == True,
        ).first()
        testeur_nom = ""
        if ep and ep.testeur_id:
            t = db.query(Testeur).filter(Testeur.id == ep.testeur_id).first()
            if t:
                testeur_nom = f"{t.nom} {t.prenom}"

        result.append({
            "id": co.id,
            "numero_ordre": co.numero_ordre,
            "famille": co.famille,
            "categorie": co.categorie,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "testeur_nom": testeur_nom,
        })

    return result