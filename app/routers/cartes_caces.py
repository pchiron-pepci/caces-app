from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_, and_
from typing import Optional
from pydantic import BaseModel
from datetime import date
from app.database import get_db
from app.models.carte_caces import CarteCaces
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire
from app.models.session_epreuve import SessionEpreuve
from app.models.testeur import Testeur

router = APIRouter(prefix="/api/cartes-caces", tags=["Cartes CACES®"])

PIN_ADMIN = "1505"


class AnnulerData(BaseModel):
    motif: Optional[str] = None


def _gen_numero(db: DBSession) -> str:
    yy = date.today().strftime("%y")
    prefix = f"PEPCI-{yy}-"
    existing = db.query(CarteCaces).filter(CarteCaces.numero_carte.like(prefix + "%")).all()
    max_n = 0
    for c in existing:
        try:
            n = int(c.numero_carte.rsplit("-", 1)[1])
            if n > max_n:
                max_n = n
        except Exception:
            pass
    return f"{prefix}{max_n + 1:05d}"


def _testeurs_map(cos: list, db: DBSession) -> dict:
    """Retourne {(stagiaire_id, session_id, categorie): testeur_nom}."""
    if not cos:
        return {}
    filtre = or_(*[
        and_(
            SessionEpreuve.stagiaire_id == co.stagiaire_id,
            SessionEpreuve.session_id == co.session_id,
            SessionEpreuve.categorie == co.categorie,
            SessionEpreuve.obtenue == True,
        )
        for co in cos
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


@router.get("/a-preparer")
def get_a_preparer(db: DBSession = Depends(get_db)):
    valides = db.query(CacesObtenu).filter(CacesObtenu.statut == "valide").all()
    if not valides:
        return []

    # Familles déjà couvertes (en_preparation ou emise)
    cartes_actives = db.query(CarteCaces).filter(
        CarteCaces.statut.in_(["en_preparation", "emise"])
    ).all()
    couvertes = {(c.stagiaire_id, c.famille) for c in cartes_actives}

    # Grouper par (stagiaire_id, famille) en excluant les couvertes
    groupes: dict = {}
    for co in valides:
        key = (co.stagiaire_id, co.famille)
        if key in couvertes:
            continue
        groupes.setdefault(key, []).append(co)

    if not groupes:
        return []

    stag_ids = {k[0] for k in groupes}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()}
    all_cos = [co for cos in groupes.values() for co in cos]
    t_map = _testeurs_map(all_cos, db)

    result = []
    for (stag_id, famille), cos in sorted(groupes.items()):
        s = stagiaires.get(stag_id)
        if not s:
            continue
        caces_list = []
        for co in cos:
            testeur = t_map.get((co.stagiaire_id, co.session_id, co.categorie), "")
            caces_list.append({
                "id": co.id,
                "categorie": co.categorie,
                "numero_ordre": co.numero_ordre,
                "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
                "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
                "testeur_nom": testeur,
            })
        caces_list.sort(key=lambda x: x["categorie"])
        result.append({
            "stagiaire_id": stag_id,
            "stagiaire_nom": s.nom,
            "stagiaire_prenom": s.prenom,
            "photo_manquante": not bool(s.photo),
            "famille": famille,
            "caces": caces_list,
        })
    return result


@router.get("/en-preparation")
def get_en_preparation(db: DBSession = Depends(get_db)):
    cartes = db.query(CarteCaces).filter(CarteCaces.statut == "en_preparation").order_by(CarteCaces.date_generation.desc()).all()
    if not cartes:
        return []
    stag_ids = {c.stagiaire_id for c in cartes}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()}
    result = []
    for c in cartes:
        s = stagiaires.get(c.stagiaire_id)
        result.append({
            "id": c.id,
            "stagiaire_id": c.stagiaire_id,
            "stagiaire_nom": s.nom if s else "?",
            "stagiaire_prenom": s.prenom if s else "",
            "famille": c.famille,
            "numero_carte": c.numero_carte,
            "date_generation": c.date_generation.isoformat(),
            "statut": c.statut,
        })
    return result


@router.get("/emises")
def get_emises(db: DBSession = Depends(get_db)):
    cartes = db.query(CarteCaces).filter(
        CarteCaces.statut.in_(["emise", "annulee"])
    ).order_by(CarteCaces.date_generation.desc()).all()
    if not cartes:
        return []
    stag_ids = {c.stagiaire_id for c in cartes}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()}
    result = []
    for c in cartes:
        s = stagiaires.get(c.stagiaire_id)
        result.append({
            "id": c.id,
            "stagiaire_id": c.stagiaire_id,
            "stagiaire_nom": s.nom if s else "?",
            "stagiaire_prenom": s.prenom if s else "",
            "famille": c.famille,
            "numero_carte": c.numero_carte,
            "date_generation": c.date_generation.isoformat(),
            "statut": c.statut,
            "motif_annulation": c.motif_annulation or "",
        })
    return result


@router.post("/preparer/{stagiaire_id}/{famille}")
def preparer_carte(stagiaire_id: int, famille: str, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    existante = db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == stagiaire_id,
        CarteCaces.famille == famille,
        CarteCaces.statut.in_(["en_preparation", "emise"]),
    ).first()
    if existante:
        raise HTTPException(status_code=400, detail="Une carte est déjà en cours pour ce stagiaire / famille")
    carte = CarteCaces(
        stagiaire_id=stagiaire_id,
        famille=famille,
        numero_carte=_gen_numero(db),
        date_generation=date.today(),
        statut="en_preparation",
    )
    db.add(carte)
    db.commit()
    return {"ok": True, "id": carte.id, "numero_carte": carte.numero_carte}


@router.post("/emettre/{carte_id}")
def emettre_carte(carte_id: int, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    if carte.statut != "en_preparation":
        raise HTTPException(status_code=400, detail="La carte n'est pas en préparation")
    carte.statut = "emise"
    db.commit()
    return {"ok": True}


@router.post("/annuler/{carte_id}")
def annuler_carte(carte_id: int, pin: str = "", data: Optional[AnnulerData] = Body(default=None), db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    carte.statut = "annulee"
    carte.motif_annulation = data.motif if data and data.motif else None
    db.commit()
    return {"ok": True}
