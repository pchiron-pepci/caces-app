from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire
from app.models.session import Session as SessionModel

router = APIRouter(prefix="/api/registre-caces", tags=["Registre CACES"])


def _nature(co: CacesObtenu) -> str:
    """3 natures : OTC (interne, y compris repris), sous-traitance, externe."""
    if not co.organisme_externe:
        return "otc"
    return "st" if co.sous_traitance else "ext"


def _mois_entre(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _statut_echeance(ech: date, aujourdhui: date, seuil_mois: int) -> str:
    if ech is None:
        return "val"
    if ech < aujourdhui:
        return "exp"
    if _mois_entre(aujourdhui, ech) <= seuil_mois:
        return "ren"
    return "val"


@router.get("")
def registre_caces(seuil: int = 6, db: DBSession = Depends(get_db)):
    """Vue a plat de tous les CACES obtenus (relance / complement).
    Exclut les CACES annules. Le calcul du statut d'echeance se fait cote
    serveur avec le seuil recu (mois). Filtres/tri restants cote front.
    """
    aujourdhui = date.today()

    # Maps stagiaire + session (evite les N+1)
    stagiaires = {s.id: s for s in db.query(Stagiaire).all()}
    sessions = {s.id: s for s in db.query(SessionModel).all()}

    records = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut != "annule")
        .all()
    )

    lignes = []
    for co in records:
        s = stagiaires.get(co.stagiaire_id)
        sess = sessions.get(co.session_id)
        ech = co.date_echeance
        lignes.append({
            "id": co.id,
            "stagiaire_id": co.stagiaire_id,
            "nom": s.nom if s else "?",
            "prenom": s.prenom if s else "?",
            "societe": (s.employeur if s else "") or "",
            "famille": co.famille,
            "categorie": co.categorie,
            "options_obtenues": co.options_obtenues or "",
            "nature": _nature(co),
            "numero": co.ancien_numero or (str(co.numero_ordre).zfill(4) if co.numero_ordre else ""),
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": ech.isoformat() if ech else None,
            "statut_echeance": _statut_echeance(ech, aujourdhui, seuil),
            "session_reference": (sess.reference if sess and sess.reference else (f"Session {co.session_id}" if co.session_id else "")),
        })

    # Tri par defaut : echeance croissante (les plus urgents en tete), None en fin
    lignes.sort(key=lambda x: (x["date_echeance"] is None, x["date_echeance"] or ""))

    # Listes distinctes pour peupler les menus deroulants cote front
    societes = sorted({l["societe"] for l in lignes if l["societe"]})
    familles = sorted({l["famille"] for l in lignes if l["famille"]})

    return {
        "seuil": seuil,
        "aujourdhui": aujourdhui.isoformat(),
        "total": len(lignes),
        "societes": societes,
        "familles": familles,
        "lignes": lignes,
    }
