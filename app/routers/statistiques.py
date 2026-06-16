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
from app.models.utilisateur import Utilisateur
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

    # batch-load grilles and users to avoid N+1
    grille_ids = {t.grille_id for t in tirages}
    grilles_map = {g.id: g for g in db.query(GrilleTheorie).filter(GrilleTheorie.id.in_(grille_ids)).all()} if grille_ids else {}

    user_ids = {t.declenche_par_id for t in tirages if t.declenche_par_id}
    users_map = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(user_ids)).all()} if user_ids else {}

    sessions_map = defaultdict(dict)
    meta_map = {}  # session_id → {date_tirage, declenche_par_id}
    for t in tirages:
        grille = grilles_map.get(t.grille_id)
        sessions_map[t.session_id][t.theme] = grille.numero if grille else "?"
        if t.session_id not in meta_map:
            meta_map[t.session_id] = {
                "date_tirage": t.date_tirage,
                "declenche_par_id": t.declenche_par_id,
            }

    session_ids = list(sessions_map.keys())
    sessions_db = {s.id: s for s in db.query(SessionModel).filter(SessionModel.id.in_(session_ids)).all()} if session_ids else {}

    historique = []
    for session_id, themes in sessions_map.items():
        session = sessions_db.get(session_id)
        meta = meta_map.get(session_id, {})
        user = users_map.get(meta.get("declenche_par_id"))
        declenche_par = f"{user.prenom} {user.nom}" if user else None
        historique.append({
            "session_id": session_id,
            "session_ref": session.reference if session else f"Session #{session_id}",
            "famille": famille,
            "themes": themes,
            "date_tirage": meta.get("date_tirage"),
            "declenche_par": declenche_par,
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

    recap_occurrences = {}
    for famille in sorted(familles):
        th_stats = stats_par_theme.get(famille, {})
        theme_keys = sorted(th_stats.keys())
        if not theme_keys:
            continue
        grilles_ref = th_stats[theme_keys[0]]
        matrix = []
        for i, g in enumerate(grilles_ref):
            row_counts = [th_stats[t][i]["count"] for t in theme_keys]
            matrix.append({
                "numero": g["grille_numero"],
                "row_counts": row_counts,
                "total": sum(row_counts),
            })
        col_totals = [sum(row["row_counts"][j] for row in matrix) for j in range(len(theme_keys))]
        for row in matrix:
            row["pct_counts"] = [
                round(row["row_counts"][j] / col_totals[j] * 100) if col_totals[j] > 0 else 0
                for j in range(len(theme_keys))
            ]
        recap_occurrences[famille] = {"themes": theme_keys, "grilles": matrix, "col_totals": col_totals}

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
            "recap_occurrences": recap_occurrences,
        }
    )
