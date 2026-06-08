from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session as DBSession
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.caces_obtenu import CacesObtenu
from app.models.config_organisme import ConfigOrganisme
from app.models.stagiaire import Stagiaire
from app.models.testeur import Testeur
from app.models.session import Session as SessionModel
from app.models.session_epreuve import SessionEpreuve
from app.models.jour_test import JourTest, ResultatTheorie
from app.services.caces_obtenus import calculer_et_synchroniser

router = APIRouter(prefix="/api/caces-obtenus", tags=["CACES® Obtenus"])

PIN_ADMIN = "1505"


class AnnulerData(BaseModel):
    motif: Optional[str] = None


class MotifUpdate(BaseModel):
    motif: str


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
        "motif_annulation": co.motif_annulation or "",
    }


def _get_theorie_pratique(co: CacesObtenu, sessions: dict, db: DBSession) -> dict:
    """Retrouve les détails théorie + pratique pour l'affichage enrichi.
    Même logique 3 priorités que _calculer_pour_epreuve dans le service.
    """
    from datetime import timedelta

    # --- Pratique ---
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
    testeur_nom = ""
    if ep and ep.testeur_id:
        t = db.query(Testeur).filter(Testeur.id == ep.testeur_id).first()
        testeur_nom = f"{t.nom} {t.prenom}" if t else ""

    # --- Théorie : 3 priorités identiques au service ---
    rt = None
    sess_theorie_id = co.session_id

    # Priorité 1 : même session
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

    # Priorité 2 : autre session ouverte, même famille, ±365 j
    if not rt and ep and ep.date:
        lim_av = ep.date - timedelta(days=365)
        lim_ap = ep.date + timedelta(days=365)
        rt = (
            db.query(ResultatTheorie)
            .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
            .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
            .filter(
                ResultatTheorie.stagiaire_id == co.stagiaire_id,
                ResultatTheorie.obtenue == True,
                ResultatTheorie.session_id != co.session_id,
                SessionModel.famille == co.famille,
                SessionModel.statut != "terminee",
                JourTest.date >= lim_av,
                JourTest.date <= lim_ap,
            )
            .order_by(ResultatTheorie.id.asc())
            .first()
        )
        if rt:
            sess_theorie_id = rt.session_id

    # Priorité 3 : session clôturée, même famille, ±365 j
    if not rt and ep and ep.date:
        lim_av = ep.date - timedelta(days=365)
        lim_ap = ep.date + timedelta(days=365)
        rt = (
            db.query(ResultatTheorie)
            .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
            .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
            .filter(
                ResultatTheorie.stagiaire_id == co.stagiaire_id,
                ResultatTheorie.obtenue == True,
                ResultatTheorie.session_id != co.session_id,
                SessionModel.famille == co.famille,
                SessionModel.statut == "terminee",
                JourTest.date >= lim_av,
                JourTest.date <= lim_ap,
            )
            .order_by(ResultatTheorie.id.asc())
            .first()
        )
        if rt:
            sess_theorie_id = rt.session_id

    jour_theo = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first() if rt else None
    date_theorie = jour_theo.date.isoformat() if jour_theo and jour_theo.date else None
    testeur_nom_theorie = ""
    if jour_theo and jour_theo.testeur_id:
        t_theo = db.query(Testeur).filter(Testeur.id == jour_theo.testeur_id).first()
        testeur_nom_theorie = f"{t_theo.nom} {t_theo.prenom}" if t_theo else ""

    sess_theorie = sessions.get(sess_theorie_id)
    if not sess_theorie and sess_theorie_id != co.session_id:
        sess_theorie = db.query(SessionModel).filter(SessionModel.id == sess_theorie_id).first()
    ref_theorie = _ref(sess_theorie)

    return {
        "date_pratique": date_pratique,
        "session_id_pratique": co.session_id,
        "session_ref_pratique": ref_pratique,
        "options_pratique": options_pratique,
        "testeur_nom": testeur_nom,
        "testeur_nom_theorie": testeur_nom_theorie,
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
    config = db.query(ConfigOrganisme).first()
    if not config:
        config = ConfigOrganisme(prochain_numero_caces=1)
        db.add(config)
    prochain = config.prochain_numero_caces if config.prochain_numero_caces is not None else 1
    co.numero_ordre = prochain
    co.statut = "valide"
    config.prochain_numero_caces = prochain + 1
    db.commit()
    return {"ok": True, "numero_ordre": co.numero_ordre}


@router.post("/annuler/{caces_id}")
def annuler_caces(caces_id: int, pin: str = "", data: Optional[AnnulerData] = Body(default=None), db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    co.statut = "annule"
    co.motif_annulation = (data.motif if data and data.motif else None)
    # Supprimer les doublons a_valider pour les mêmes clés — seront recalculés au prochain /a-valider
    db.query(CacesObtenu).filter(
        CacesObtenu.id != caces_id,
        CacesObtenu.stagiaire_id == co.stagiaire_id,
        CacesObtenu.session_id == co.session_id,
        CacesObtenu.categorie == co.categorie,
        CacesObtenu.statut == "a_valider",
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.patch("/{caces_id}/motif")
def update_motif(caces_id: int, data: MotifUpdate, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    co.motif_annulation = data.motif
    db.commit()
    return {"ok": True}
