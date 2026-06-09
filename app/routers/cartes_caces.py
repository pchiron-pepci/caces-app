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
from app.models.config_organisme import ConfigOrganisme

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


def _img_uri(b64, nom):
    if not b64:
        return ""
    ext = (nom or "").rsplit(".", 1)[-1].lower() if nom and "." in (nom or "") else "png"
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


def _build_print_data(carte, s, cos, t_map, config):
    cfg = config or ConfigOrganisme()
    return {
        "id": carte.id,
        "numero_carte": carte.numero_carte,
        "date_generation": carte.date_generation.isoformat(),
        "stagiaire_id": s.id,
        "stagiaire_nom": s.nom,
        "stagiaire_prenom": s.prenom,
        "photo_url": s.photo or "",
        "famille": carte.famille,
        "caces": [
            {
                "categorie": co.categorie,
                "numero_ordre": co.numero_ordre,
                "options_obtenues": co.options_obtenues or "",
                "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
                "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
                "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
            }
            for co in sorted(cos, key=lambda x: x.categorie)
        ],
        "config": {
            "nom_organisme": cfg.nom_organisme or "",
            "logo_uri": _img_uri(cfg.logo_base64, cfg.logo_nom),
            "url_verification_caces": cfg.url_verification_caces or "",
        },
    }


# ===== LECTURE =====

@router.get("/stagiaires")
def get_stagiaires(db: DBSession = Depends(get_db)):
    stag_ids = [r[0] for r in db.query(CacesObtenu.stagiaire_id).filter(CacesObtenu.statut == "valide").distinct().all()]
    if not stag_ids:
        return []
    stagiaires = (
        db.query(Stagiaire)
        .filter(Stagiaire.id.in_(stag_ids), Stagiaire.actif == True)
        .order_by(Stagiaire.nom, Stagiaire.prenom)
        .all()
    )
    return [{"id": s.id, "nom": s.nom, "prenom": s.prenom} for s in stagiaires]


@router.get("/familles/{stagiaire_id}")
def get_familles(stagiaire_id: int, db: DBSession = Depends(get_db)):
    rows = db.query(CacesObtenu.famille).filter(
        CacesObtenu.stagiaire_id == stagiaire_id,
        CacesObtenu.statut == "valide",
    ).distinct().all()
    return sorted([r[0] for r in rows])


@router.get("/caces-valides/{stagiaire_id}/{famille}")
def get_caces_valides(stagiaire_id: int, famille: str, db: DBSession = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404)
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == stagiaire_id, CacesObtenu.famille == famille, CacesObtenu.statut == "valide")
        .order_by(CacesObtenu.categorie)
        .all()
    )
    t_map = _testeurs_map(cos, db)
    return {
        "stagiaire_id": s.id,
        "stagiaire_nom": s.nom,
        "stagiaire_prenom": s.prenom,
        "photo_url": s.photo or "",
        "photo_manquante": not bool(s.photo),
        "famille": famille,
        "caces": [
            {
                "id": co.id,
                "categorie": co.categorie,
                "numero_ordre": co.numero_ordre,
                "options_obtenues": co.options_obtenues or "",
                "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
                "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
                "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
            }
            for co in cos
        ],
    }


@router.get("/emises")
def get_emises(db: DBSession = Depends(get_db)):
    cartes = (
        db.query(CarteCaces)
        .filter(CarteCaces.statut.in_(["emise", "remplacee", "annulee"]))
        .order_by(CarteCaces.date_generation.desc())
        .all()
    )
    if not cartes:
        return []
    stag_ids = {c.stagiaire_id for c in cartes}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()}
    return [
        {
            "id": c.id,
            "stagiaire_id": c.stagiaire_id,
            "stagiaire_nom": stagiaires[c.stagiaire_id].nom if c.stagiaire_id in stagiaires else "?",
            "stagiaire_prenom": stagiaires[c.stagiaire_id].prenom if c.stagiaire_id in stagiaires else "",
            "famille": c.famille,
            "numero_carte": c.numero_carte,
            "date_generation": c.date_generation.isoformat(),
            "statut": c.statut,
            "motif_annulation": c.motif_annulation or "",
        }
        for c in cartes
    ]


@router.get("/reimprimer/{carte_id}")
def reimprimer_carte(carte_id: int, db: DBSession = Depends(get_db)):
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    s = db.query(Stagiaire).filter(Stagiaire.id == carte.stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404)
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == carte.stagiaire_id, CacesObtenu.famille == carte.famille, CacesObtenu.statut == "valide")
        .all()
    )
    t_map = _testeurs_map(cos, db)
    config = db.query(ConfigOrganisme).first()
    return _build_print_data(carte, s, cos, t_map, config)


# ===== ACTIONS =====

@router.post("/emettre/{stagiaire_id}/{famille}")
def emettre_carte(stagiaire_id: int, famille: str, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    s = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")
    if not s.photo:
        raise HTTPException(status_code=400, detail="Photo manquante — impossible d'émettre la carte")
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == stagiaire_id, CacesObtenu.famille == famille, CacesObtenu.statut == "valide")
        .all()
    )
    if not cos:
        raise HTTPException(status_code=400, detail="Aucun CACES® valide pour ce stagiaire / famille")
    # Remplace l'ancienne carte émise
    db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == stagiaire_id,
        CarteCaces.famille == famille,
        CarteCaces.statut == "emise",
    ).update({"statut": "remplacee"})
    carte = CarteCaces(
        stagiaire_id=stagiaire_id,
        famille=famille,
        numero_carte=_gen_numero(db),
        date_generation=date.today(),
        statut="emise",
    )
    db.add(carte)
    db.commit()
    db.refresh(carte)
    t_map = _testeurs_map(cos, db)
    config = db.query(ConfigOrganisme).first()
    return _build_print_data(carte, s, cos, t_map, config)


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
