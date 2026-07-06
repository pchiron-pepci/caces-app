from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.config_utils import get_pin_admin
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
    numero_nda: Optional[str] = None
    date_habilitation: Optional[date] = None
    date_expiration_habilitation: Optional[date] = None
    visite_medicale: Optional[date] = None
    visite_medicale_date: Optional[date] = None
    evaluation_date: Optional[date] = None
    formation_continue: Optional[date] = None
    date_prochain_controle: Optional[date] = None
    note: Optional[str] = None
    utilisateur_id: Optional[int] = None

class TesteurResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    statut: str
    entreprise: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    numero_inrs: Optional[str] = None
    numero_nda: Optional[str] = None
    date_habilitation: Optional[date] = None
    date_expiration_habilitation: Optional[date] = None
    visite_medicale: Optional[date] = None
    formation_continue: Optional[date] = None
    date_prochain_controle: Optional[date] = None
    note: Optional[str] = None
    actif: bool
    utilisateur_id: Optional[int] = None

    class Config:
        from_attributes = True

@router.get("/", response_model=list[TesteurResponse])
def liste_testeurs(db: Session = Depends(get_db)):
    return db.query(Testeur).filter(Testeur.actif == True).all()

@router.get("/habilites")
def testeurs_habilites(famille: str, request: Request, db: Session = Depends(get_db),
                       categorie: str = None, options: str = None):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    if not famille:
        raise HTTPException(status_code=422, detail="Paramètre famille requis")
    # Options = lignes d'habilitation distinctes (categorie 'OPT-PE', 'OPT-TEL').
    # Testeur valide s'il couvre la categorie ET chaque option requise.
    req = set(o.strip().upper() for o in (options or "").split(",") if o.strip())
    cats_requises = set()
    if categorie:
        cats_requises.add(categorie)
    for o in req:
        cats_requises.add("OPT-" + o)

    rows = (
        db.query(Testeur, HabilitationTesteur)
        .join(HabilitationTesteur, HabilitationTesteur.testeur_id == Testeur.id)
        .filter(
            HabilitationTesteur.famille == famille,
            HabilitationTesteur.actif == True,
            Testeur.actif == True,
            Testeur.etat == "actif",
        )
        .order_by(Testeur.nom, Testeur.prenom)
        .all()
    )

    cats_par_testeur = {}
    testeur_info = {}
    for t, hab in rows:
        cats_par_testeur.setdefault(t.id, set()).add(hab.categorie)
        testeur_info[t.id] = t

    out = []
    for tid, cats in cats_par_testeur.items():
        if cats_requises.issubset(cats):
            t = testeur_info[tid]
            out.append({"id": t.id, "nom": t.nom, "prenom": t.prenom})
    return out

@router.get("/{id}", response_model=TesteurResponse)
def get_testeur(id: int, db: Session = Depends(get_db)):
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    return t

def _verifier_unicite_utilisateur(db: Session, utilisateur_id: int, exclude_id: int = None):
    if utilisateur_id is None:
        return
    q = db.query(Testeur).filter(Testeur.utilisateur_id == utilisateur_id)
    if exclude_id is not None:
        q = q.filter(Testeur.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Ce compte utilisateur est déjà associé à une autre fiche testeur")

@router.post("/", response_model=TesteurResponse)
def create_testeur(data: TesteurCreate, db: Session = Depends(get_db)):
    _verifier_unicite_utilisateur(db, data.utilisateur_id)
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
    _verifier_unicite_utilisateur(db, data.utilisateur_id, exclude_id=id)
    for key, value in data.model_dump(exclude={'etat'}).items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return t

@router.put("/{id}/etat")
def update_etat_testeur(id: int, pin: str, etat: str, db: Session = Depends(get_db)):
    if pin != get_pin_admin(db):
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
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    t = db.query(Testeur).filter(Testeur.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testeur non trouve")
    t.actif = False
    db.commit()
    return {"message": "Testeur archive"}