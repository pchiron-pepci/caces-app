from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict

from app.database import get_db
from app.config_utils import get_pin_admin
from app.models.grille_theorie import GrilleTheorie
from app.models.utilisations_themes import UtilisationTheme
from app.models.session import Session as SessionModel
from app.templates_instance import templates

router = APIRouter()

THEME_NOMS = {
    "R482": {
        1: "Thème 1 — Connaissances générales (12 pts)",
        2: "Thème 2 — Technologie et stabilité (28 pts)",
        3: "Thème 3 — Exploitation des engins (44 pts)",
        4: "Thème 4 — Circulation (12 pts)",
        5: "Thème 5 — Fin de poste / Maintenance (4 pts)",
    },
    "R486": {
        1: "Thème 1 — Connaissances générales",
        2: "Thème 2 — Technologie",
        3: "Thème 3 — Exploitation",
        4: "Thème 4 — Circulation",
        5: "Thème 5 — Fin de poste",
    },
    "R489": {
        1: "Thème 1 — Connaissances générales",
        2: "Thème 2 — Technologie",
        3: "Thème 3 — Exploitation",
        4: "Thème 4 — Circulation",
        5: "Thème 5 — Fin de poste",
    },
}


def _build_stats(famille, annee, db):
    grilles = (
        db.query(GrilleTheorie)
        .filter(GrilleTheorie.famille == famille, GrilleTheorie.actif == True)
        .order_by(GrilleTheorie.numero)
        .all()
    )

    rows = (
        db.query(
            UtilisationTheme.theme,
            UtilisationTheme.grille_id,
            func.count(UtilisationTheme.id).label("cnt")
        )
        .filter(
            UtilisationTheme.famille == famille,
            UtilisationTheme.annee == annee
        )
        .group_by(UtilisationTheme.theme, UtilisationTheme.grille_id)
        .all()
    )

    usage = defaultdict(lambda: defaultdict(int))
    for theme, grille_id, cnt in rows:
        usage[theme][grille_id] = cnt

    themes = sorted(THEME_NOMS.get(famille, {}).keys())

    stats_par_theme = {}
    alertes = []
    total_sessions = (
        db.query(UtilisationTheme.session_id)
        .filter(
            UtilisationTheme.famille == famille,
            UtilisationTheme.annee == annee
        )
        .distinct()
        .count()
    )

    for theme in themes:
        total_theme = sum(usage[theme].values()) or 1

        grilles_stats = []
        for g in grilles:
            count = usage[theme].get(g.id, 0)
            pct = round(count / total_theme * 100) if sum(usage[theme].values()) > 0 else 0

            if count == 0:
                statut = "VIDE"
            elif pct < 10:
                statut = "SOUS"
            elif pct > 30:
                statut = "SUR"
            else:
                statut = "OK"

            if statut in ("SOUS", "SUR") and sum(usage[theme].values()) >= 5:
                alertes.append({
                    "famille": famille,
                    "theme_nom": THEME_NOMS.get(famille, {}).get(theme, f"Thème {theme}"),
                    "grille_numero": g.numero,
                    "pct": pct,
                    "statut": statut,
                })

            grilles_stats.append({
                "grille_numero": g.numero,
                "grille_id": g.id,
                "count": count,
                "pct": pct,
                "statut": statut,
            })

        stats_par_theme[theme] = grilles_stats

    return stats_par_theme, alertes, total_sessions


def _build_historique(famille, annee, db):
    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.famille == famille,
            UtilisationTheme.annee == annee
        )
        .order_by(UtilisationTheme.session_id, UtilisationTheme.theme)
        .all()
    )

    sessions_map = defaultdict(dict)
    for t in tirages:
        grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == t.grille_id).first()
        sessions_map[t.session_id][t.theme] = grille.numero if grille else "?"

    historique = []
    for session_id, themes in sessions_map.items():
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        historique.append({
            "session_ref": session.reference if session else f"Session #{session_id}",
            "famille": famille,
            "themes": themes,
        })

    return historique


@router.get("/statistiques", response_class=HTMLResponse)
async def page_statistiques(request: Request, db: DBSession = Depends(get_db)):
    annee = datetime.now().year

    familles = [
        row[0] for row in
        db.query(GrilleTheorie.famille)
        .filter(GrilleTheorie.actif == True)
        .distinct()
        .all()
    ]

    stats_par_theme = {}
    totaux_famille = {}
    all_alertes = []
    historique = []

    for famille in sorted(familles):
        th_stats, alertes, total = _build_stats(famille, annee, db)
        stats_par_theme[famille] = th_stats
        totaux_famille[famille] = total
        all_alertes.extend(alertes)
        historique.extend(_build_historique(famille, annee, db))

    return templates.TemplateResponse(
        request=request,
        name="statistiques.html",
        context={
            "annee": annee,
            "stats_par_theme": stats_par_theme,
            "totaux_famille": totaux_famille,
            "theme_noms": THEME_NOMS,
            "alertes": all_alertes,
            "historique": historique,
        }
    )


@router.post("/api/statistiques/reset-themes")
async def reset_themes(pin: str = None, db: DBSession = Depends(get_db)):
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN incorrect")
    annee = datetime.now().year
    nb = db.query(UtilisationTheme).filter(UtilisationTheme.annee == annee).delete()
    db.commit()
    return {"message": f"{nb} enregistrement(s) supprimé(s)"}