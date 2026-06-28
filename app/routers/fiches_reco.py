"""
app/routers/fiches_reco.py

Routes de la fiche de recommandation de formation (morceau 3a : charger + enregistrer).

GET  /api/fiches-reco/{session_id}/{stagiaire_id}        -> données pré-remplies (calcul)
                                                            fusionnées avec le brouillon stocké
POST /api/fiches-reco/{session_id}/{stagiaire_id}        -> enregistre/maj le brouillon (saisies testeur)

Le pré-remplissage vient de calculer_fiche_reco (lecture seule, étape 1).
Les saisies du testeur (cases + durées ajustées + autres) sont stockées dans FicheRecommandation.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel

from app.database import get_db
from app.models.fiche_recommandation import FicheRecommandation
from app.services.calcul_fiche_reco import calculer_fiche_reco

router = APIRouter(prefix="/api/fiches-reco", tags=["Fiches recommandation"])


class FicheBrouillon(BaseModel):
    fraude_theorie: bool = False
    difficultes_langue: bool = False
    comportement_dangereux: bool = False
    autres_precisions: Optional[str] = None
    # saisies libres : { "theorie": "<duree>", "pratiques": { "B1": {"duree": "...", "cause": "..."} } }
    saisies: Optional[dict] = None
    testeur_id: Optional[int] = None
    testeur_nom: Optional[str] = None


def _fiche_dict(fiche: FicheRecommandation) -> dict:
    """Sérialise les saisies stockées (None si pas encore de brouillon)."""
    if not fiche:
        return {
            "existe": False, "statut": None,
            "fraude_theorie": False, "difficultes_langue": False,
            "comportement_dangereux": False, "autres_precisions": None,
            "saisies": None, "testeur_id": None, "testeur_nom": None,
        }
    saisies = None
    if fiche.saisies_json:
        try:
            saisies = json.loads(fiche.saisies_json)
        except (ValueError, TypeError):
            saisies = None
    return {
        "existe": True,
        "statut": fiche.statut,
        "fraude_theorie": bool(fiche.fraude_theorie),
        "difficultes_langue": bool(fiche.difficultes_langue),
        "comportement_dangereux": bool(fiche.comportement_dangereux),
        "autres_precisions": fiche.autres_precisions,
        "saisies": saisies,
        "testeur_id": fiche.testeur_id,
        "testeur_nom": fiche.testeur_nom,
    }


@router.get("/{session_id}/{stagiaire_id}")
def charger_fiche(session_id: int, stagiaire_id: int, db: DBSession = Depends(get_db)):
    """Renvoie le pré-remplissage (calcul) + le brouillon stocké si existant."""
    calcul = calculer_fiche_reco(session_id, stagiaire_id, db)
    fiche = db.query(FicheRecommandation).filter(
        FicheRecommandation.session_id == session_id,
        FicheRecommandation.stagiaire_id == stagiaire_id,
    ).order_by(FicheRecommandation.id.desc()).first()
    return {
        "calcul": calcul,
        "fiche": _fiche_dict(fiche),
    }


@router.post("/{session_id}/{stagiaire_id}")
def enregistrer_brouillon(session_id: int, stagiaire_id: int,
                          data: FicheBrouillon, db: DBSession = Depends(get_db)):
    """Crée ou met à jour le brouillon (saisies testeur). Ne finalise pas."""
    fiche = db.query(FicheRecommandation).filter(
        FicheRecommandation.session_id == session_id,
        FicheRecommandation.stagiaire_id == stagiaire_id,
    ).order_by(FicheRecommandation.id.desc()).first()

    if fiche is None:
        fiche = FicheRecommandation(
            session_id=session_id, stagiaire_id=stagiaire_id, statut="brouillon",
        )
        db.add(fiche)

    # une fiche finalisée reste modifiable (décision produit) -> on autorise la maj
    fiche.fraude_theorie = bool(data.fraude_theorie)
    fiche.difficultes_langue = bool(data.difficultes_langue)
    fiche.comportement_dangereux = bool(data.comportement_dangereux)
    fiche.autres_precisions = data.autres_precisions
    fiche.saisies_json = json.dumps(data.saisies, ensure_ascii=False) if data.saisies is not None else None
    if data.testeur_id is not None:
        fiche.testeur_id = data.testeur_id
    if data.testeur_nom is not None:
        fiche.testeur_nom = data.testeur_nom

    db.commit()
    db.refresh(fiche)
    return {"ok": True, "fiche_id": fiche.id, "statut": fiche.statut}