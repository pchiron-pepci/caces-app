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
from app.models.session_candidat import SessionCandidat
from app.services.caces_obtenus import calculer_et_synchroniser
from app.config_utils import get_pin_admin

router = APIRouter(prefix="/api/caces-obtenus", tags=["CACES® Obtenus"])


class AnnulerData(BaseModel):
    motif: Optional[str] = None
    bloquer_pratique: bool = False
    bloquer_theorie: bool = False


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
        "stagiaire_ddn": s.date_naissance.isoformat() if s and s.date_naissance else None,
        "session_id": co.session_id,
        "session_reference": _ref(sess),
        "famille": co.famille,
        "categorie": co.categorie,
        "options_obtenues": co.options_obtenues or "",
        "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
        "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
        "numero_ordre": co.numero_ordre,
        "ancien_numero": co.ancien_numero,
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

    # --- Théorie : on AFFICHE la decision du moteur (resultat_theorie_id stocke), pas de recalcul ---
    rt = None
    date_theorie = None
    sess_theorie_id = None
    ref_theorie = None
    testeur_nom_theorie = None
    if co.resultat_theorie_id is not None:
        rt = db.query(ResultatTheorie).filter(
            ResultatTheorie.id == co.resultat_theorie_id
        ).first()
        if rt:
            _jt = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
            date_theorie = _jt.date if _jt and _jt.date else None
            sess_theorie_id = rt.session_id
            _sess_t = sessions.get(rt.session_id)
            ref_theorie = (_sess_t.reference if _sess_t else None) or (f"Session {rt.session_id}" if rt.session_id else None)
            _tid = getattr(rt, "testeur_id", None)
            if _tid:
                _t = db.query(Testeur).filter(Testeur.id == _tid).first()
                testeur_nom_theorie = (f"{_t.prenom[0]}. {_t.nom}" if _t and _t.prenom else (_t.nom if _t else None))
    # post_cloture reel = celui stocke sur le CACES (decision du moteur), pas un recalcul
    _post_cloture_aff = bool(getattr(co, "post_cloture", False))

    # --- Bloc dispense (affichage CACES obtenus) ---
    dispense_info = None
    sc_disp = (
        db.query(SessionCandidat)
        .filter(
            SessionCandidat.session_id == co.session_id,
            SessionCandidat.stagiaire_id == co.stagiaire_id,
            SessionCandidat.actif == True,
        )
        .first()
    )
    if sc_disp and sc_disp.theorie_dispensee and sc_disp.dispense_origine in ("interne", "externe"):
        dispense_info = {
            "origine":   sc_disp.dispense_origine,
            "date_base": sc_disp.dispense_date.isoformat() if sc_disp.dispense_date else None,
            "echeance":  sc_disp.dispense_echeance.isoformat() if sc_disp.dispense_echeance else None,
            "justif":    bool(sc_disp.dispense_fichier_cle),
            "sc_id":     sc_disp.id,
        }

    # Fallback : pas de dispense saisie MAIS le CACES est une extension (caces_initial_id rempli)
    # -> construire une dispense implicite "interne" basee sur le CACES de base (cas 5/6).
    if dispense_info is None and getattr(co, "caces_initial_id", None):
        _base = db.query(CacesObtenu).filter(CacesObtenu.id == co.caces_initial_id).first()
        if _base and _base.date_obtention:
            dispense_info = {
                "origine":   "interne",
                "date_base": _base.date_obtention.isoformat(),
                "echeance":  None,
                "justif":    False,
                "sc_id":     None,
            }

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
        "post_cloture": _post_cloture_aff,
        "dispense": dispense_info,
    }


def _bulk_maps(records: list, db: DBSession):
    ids_s = {r.stagiaire_id for r in records}
    ids_sess = {r.session_id for r in records}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(ids_s)).all()} if ids_s else {}
    sessions = {s.id: s for s in db.query(SessionModel).filter(SessionModel.id.in_(ids_sess)).all()} if ids_sess else {}
    return stagiaires, sessions


def _bulk_testeurs(records: list, db: DBSession) -> dict:
    """Retourne {(stagiaire_id, session_id, categorie): testeur_nom} via SessionEpreuve."""
    if not records:
        return {}
    from sqlalchemy import or_, and_
    filtre = or_(*[
        and_(
            SessionEpreuve.stagiaire_id == r.stagiaire_id,
            SessionEpreuve.session_id == r.session_id,
            SessionEpreuve.categorie == r.categorie,
            SessionEpreuve.obtenue == True,
        )
        for r in records
    ])
    epreuves = db.query(SessionEpreuve).filter(filtre).all()
    t_ids = {ep.testeur_id for ep in epreuves if ep.testeur_id}
    testeurs = {t.id: t for t in db.query(Testeur).filter(Testeur.id.in_(t_ids)).all()} if t_ids else {}
    result = {}
    for ep in epreuves:
        k = (ep.stagiaire_id, ep.session_id, ep.categorie)
        t = testeurs.get(ep.testeur_id)
        result[k] = f"{t.nom} {t.prenom}" if t else ""
    return result


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
        .filter(
            CacesObtenu.statut.in_(["valide", "annule"]),
            CacesObtenu.organisme_externe.is_(None),  # exclut les CACES externes (affichage PEPCI uniquement ; moteur d'extension non impacte)
        )
        .order_by(CacesObtenu.numero_ordre.desc())
        .all()
    )
    stagiaires, sessions = _bulk_maps(records, db)
    result = []
    for r in records:
        item = _enrich_base(r, stagiaires, sessions)
        item.update(_get_theorie_pratique(r, sessions, db))
        result.append(item)
    return result


@router.post("/valider/{caces_id}")
def valider_caces(caces_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    if co.statut != "a_valider":
        raise HTTPException(status_code=400, detail="Ce CACES® n'est pas en attente de validation")
    # G2 : bloquer si un ANTERIEUR a_valider partage la MEME BASE (ordre chronologique)
    _base_q = db.query(CacesObtenu).filter(
        CacesObtenu.stagiaire_id == co.stagiaire_id,
        CacesObtenu.famille == co.famille,
        CacesObtenu.statut == "a_valider",
        CacesObtenu.date_obtention < co.date_obtention,
        CacesObtenu.id != co.id,
    )
    # base partagee n.1 : meme theorie fondatrice
    plus_ancien = None
    if co.resultat_theorie_id is not None:
        plus_ancien = _base_q.filter(
            CacesObtenu.resultat_theorie_id == co.resultat_theorie_id
        ).order_by(CacesObtenu.date_obtention.asc()).first()
    # base partagee n.2 : co est une extension qui herite de cet anterieur
    if plus_ancien is None and co.caces_initial_id is not None:
        plus_ancien = _base_q.filter(
            CacesObtenu.id == co.caces_initial_id
        ).order_by(CacesObtenu.date_obtention.asc()).first()
    if plus_ancien is not None:
        raise HTTPException(status_code=409, detail=(
            "validation hors ordre - validez d'abord le CACES plus ancien "
            f"(categorie {plus_ancien.categorie}, obtenu le {plus_ancien.date_obtention}) "
            "qui partage la meme base theorique."
        ))
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
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    motif = data.motif if data and data.motif else None
    bloquer_pratique = data.bloquer_pratique if data else False
    bloquer_theorie = data.bloquer_theorie if data else False

    co.statut = "annule"
    co.motif_annulation = motif

    # Bloquer SE si demandé (empêche re-création auto CACES®)
    if bloquer_pratique:
        ep = (
            db.query(SessionEpreuve)
            .filter(
                SessionEpreuve.session_id == co.session_id,
                SessionEpreuve.stagiaire_id == co.stagiaire_id,
                SessionEpreuve.categorie == co.categorie,
                SessionEpreuve.obtenue == True,
            )
            .first()
        )
        if ep:
            ep.bloque = True

    # Bloquer RT si demandé (toute la famille pour ce stagiaire dans cette session)
    if bloquer_theorie:
        rts = (
            db.query(ResultatTheorie)
            .filter(
                ResultatTheorie.session_id == co.session_id,
                ResultatTheorie.stagiaire_id == co.stagiaire_id,
                ResultatTheorie.obtenue == True,
            )
            .all()
        )
        for rt in rts:
            rt.bloque = True

    # Supprimer les doublons a_valider — seront recalculés au prochain /a-valider si non bloqués
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
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="PIN incorrect")
    co = db.query(CacesObtenu).filter(CacesObtenu.id == caces_id).first()
    if not co:
        raise HTTPException(status_code=404, detail="Non trouvé")
    co.motif_annulation = data.motif
    db.commit()
    return {"ok": True}
