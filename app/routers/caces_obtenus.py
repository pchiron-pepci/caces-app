from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from app.database import get_db
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire
from app.models.session import Session as SessionModel
from app.services.caces_obtenus import calculer_et_synchroniser

router = APIRouter(prefix="/api/caces-obtenus", tags=["CACES® Obtenus"])

PIN_ADMIN = "1505"


def _enrich(co: CacesObtenu, stagiaires: dict, sessions: dict) -> dict:
    s = stagiaires.get(co.stagiaire_id)
    sess = sessions.get(co.session_id)
    return {
        "id": co.id,
        "stagiaire_id": co.stagiaire_id,
        "stagiaire_nom": s.nom if s else "?",
        "stagiaire_prenom": s.prenom if s else "?",
        "session_id": co.session_id,
        "session_reference": (sess.reference or f"Session {co.session_id}") if sess else f"Session {co.session_id}",
        "famille": co.famille,
        "categorie": co.categorie,
        "options_obtenues": co.options_obtenues or "",
        "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
        "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
        "numero_ordre": co.numero_ordre,
        "statut": co.statut,
    }


def _bulk_maps(records: list, db: DBSession):
    ids_s = {r.stagiaire_id for r in records}
    ids_sess = {r.session_id for r in records}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(ids_s)).all()} if ids_s else {}
    sessions = {s.id: s for s in db.query(SessionModel).filter(SessionModel.id.in_(ids_sess)).all()} if ids_sess else {}
    return stagiaires, sessions


@router.get("/a-valider")
def get_a_valider(db: DBSession = Depends(get_db)):
    records = calculer_et_synchroniser(db)
    stagiaires, sessions = _bulk_maps(records, db)
    return [_enrich(r, stagiaires, sessions) for r in records]


@router.get("/valides")
def get_valides(db: DBSession = Depends(get_db)):
    records = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut.in_(["valide", "annule"]))
        .order_by(CacesObtenu.numero_ordre.desc())
        .all()
    )
    stagiaires, sessions = _bulk_maps(records, db)
    return [_enrich(r, stagiaires, sessions) for r in records]


@router.post("/valider/{caces_id}")
def valider_caces(caces_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    if co.statut != "a_valider":
        raise HTTPException(status_code=400, detail="Ce CACES® n'est pas en attente de validation")
    max_no = db.query(func.max(CacesObtenu.numero_ordre)).scalar() or 0
    co.numero_ordre = max_no + 1
    co.statut = "valide"
    db.commit()
    return {"ok": True, "numero_ordre": co.numero_ordre}


@router.post("/annuler/{caces_id}")
def annuler_caces(caces_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    co.statut = "annule"
    db.commit()
    return {"ok": True}
