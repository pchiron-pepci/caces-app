from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from app.database import get_db
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire
from app.models.session import Session as SessionModel
from app.models.session_epreuve import SessionEpreuve
from app.models.jour_test import JourTest, ResultatTheorie
from app.services.caces_obtenus import calculer_et_synchroniser

router = APIRouter(prefix="/api/caces-obtenus", tags=["CACES® Obtenus"])

PIN_ADMIN = "1505"


def _ref(sess) -> str:
    if not sess:
        return "—"
    return sess.reference or f"Session {sess.id}"


def _enrich_base(co: CacesObtenu, stagiaires: dict, sessions: dict) -> dict:
    s = stagiaires.get(co.stagiaire_id)
    sess = sessions.get(co.session_id)
    return {
        "id": co.id,
        "stagiaire_id": co.stagiaire_id,
        "stagiaire_nom": s.nom if s else "?",
        "stagiaire_prenom": s.prenom if s else "?",
        "session_id": co.session_id,
        "session_reference": _ref(sess),
        "famille": co.famille,
        "categorie": co.categorie,
        "options_obtenues": co.options_obtenues or "",
        "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
        "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
        "numero_ordre": co.numero_ordre,
        "statut": co.statut,
    }


def _get_theorie_pratique(co: CacesObtenu, sessions: dict, db: DBSession) -> dict:
    """Retrouve les détails théorie + pratique pour l'affichage enrichi."""
    # Pratique : épreuve source
    ep = (
        db.query(SessionEpreuve)
        .filter(
            SessionEpreuve.session_id == co.session_id,
            SessionEpreuve.stagiaire_id == co.stagiaire_id,
            SessionEpreuve.categorie == co.categorie,
            SessionEpreuve.obtenue == True,
        )
        .order_by(SessionEpreuve.id.desc())
        .first()
    )
    date_pratique = ep.date.isoformat() if ep and ep.date else None
    options_pratique = ep.options_obtenues or "" if ep else ""
    sess_pratique = sessions.get(co.session_id)
    ref_pratique = _ref(sess_pratique)

    # Théorie : même session d'abord, sinon post-clôture
    rt = (
        db.query(ResultatTheorie)
        .filter(
            ResultatTheorie.stagiaire_id == co.stagiaire_id,
            ResultatTheorie.session_id == co.session_id,
            ResultatTheorie.obtenue == True,
        )
        .order_by(ResultatTheorie.id.asc())
        .first()
    )
    sess_theorie_id = co.session_id
    if not rt:
        rt = (
            db.query(ResultatTheorie)
            .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
            .filter(
                ResultatTheorie.stagiaire_id == co.stagiaire_id,
                ResultatTheorie.obtenue == True,
                SessionModel.famille == co.famille,
                SessionModel.statut == "terminee",
            )
            .order_by(ResultatTheorie.id.asc())
            .first()
        )
        if rt:
            sess_theorie_id = rt.session_id

    jour_theo = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first() if rt else None
    date_theorie = jour_theo.date.isoformat() if jour_theo and jour_theo.date else None

    sess_theorie = sessions.get(sess_theorie_id)
    if not sess_theorie and sess_theorie_id != co.session_id:
        sess_theorie = db.query(SessionModel).filter(SessionModel.id == sess_theorie_id).first()
    ref_theorie = _ref(sess_theorie)

    return {
        "date_pratique": date_pratique,
        "session_id_pratique": co.session_id,
        "session_ref_pratique": ref_pratique,
        "options_pratique": options_pratique,
        "date_theorie": date_theorie,
        "session_id_theorie": sess_theorie_id,
        "session_ref_theorie": ref_theorie,
        "post_cloture": sess_theorie_id != co.session_id,
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
    result = []
    for r in records:
        item = _enrich_base(r, stagiaires, sessions)
        item.update(_get_theorie_pratique(r, sessions, db))
        result.append(item)
    return result


@router.get("/valides")
def get_valides(db: DBSession = Depends(get_db)):
    records = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut.in_(["valide", "annule"]))
        .order_by(CacesObtenu.numero_ordre.desc())
        .all()
    )
    stagiaires, sessions = _bulk_maps(records, db)
    return [_enrich_base(r, stagiaires, sessions) for r in records]


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
