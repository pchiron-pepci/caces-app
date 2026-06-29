from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, and_
from app.models.reset_tirage import resets_famille, ResetTirage
from app.models.config_organisme import ConfigOrganisme
from datetime import datetime, date
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


def _filtre_periode(debut, fin):
    """Critere de filtrage d'UtilisationTheme sur l'intervalle (debut, fin].
    debut/fin sont des datetime de reset (ou None pour borne ouverte).
    Tirage rattache a la periode par sa date_tirage. Les tirages sans date
    (anciens) ne sont rattaches qu'a la periode 'depuis le demarrage' (debut None)."""
    conds = []
    if debut is not None:
        conds.append(UtilisationTheme.date_tirage > debut)
    if fin is not None:
        conds.append(UtilisationTheme.date_tirage <= fin)
    if not conds:
        return None
    return and_(*conds)


def _build_stats(famille, debut, fin, db):
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
            *([_fp] if (_fp := _filtre_periode(debut, fin)) is not None else [])
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
            *([_fp2] if (_fp2 := _filtre_periode(debut, fin)) is not None else [])
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


def _build_historique(famille, db):
    tirages = (
        db.query(UtilisationTheme)
        .filter(UtilisationTheme.famille == famille)
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


def _periodes_famille(famille, db):
    """Construit la liste des periodes selectionnables pour une famille,
    bornees par les resets. Index 0 = periode en cours (depuis dernier reset
    ou depuis le demarrage). Ajoute toujours une entree 'tout' en fin."""
    resets = resets_famille(famille, db)  # plus recent d'abord
    periodes = []
    if not resets:
        periodes.append({
            "id": "0", "label": "Depuis le démarrage",
            "debut": None, "fin": None,
        })
    else:
        # periode en cours : depuis le dernier reset jusqu'a maintenant
        periodes.append({
            "id": "0",
            "label": "Période en cours (depuis le %s)" % resets[0].date_reset.strftime("%d/%m/%Y"),
            "debut": resets[0].date_reset, "fin": None,
        })
        # periodes intermediaires entre resets consecutifs
        for i in range(len(resets) - 1):
            fin = resets[i].date_reset
            debut = resets[i + 1].date_reset
            periodes.append({
                "id": str(i + 1),
                "label": "Période %s → %s" % (
                    debut.strftime("%d/%m/%Y"), fin.strftime("%d/%m/%Y")),
                "debut": debut, "fin": fin,
            })
        # premiere periode : du demarrage au plus ancien reset
        periodes.append({
            "id": str(len(resets)),
            "label": "Depuis le démarrage → %s" % resets[-1].date_reset.strftime("%d/%m/%Y"),
            "debut": None, "fin": resets[-1].date_reset,
        })
    periodes.append({"id": "tout", "label": "Tout l'historique", "debut": None, "fin": None})
    return periodes


@router.get("/statistiques", response_class=HTMLResponse)
async def page_statistiques(request: Request, db: DBSession = Depends(get_db)):
    _config = db.query(ConfigOrganisme).first()

    familles = [
        row[0] for row in
        db.query(GrilleTheorie.famille)
        .filter(GrilleTheorie.actif == True)
        .distinct()
        .all()
    ]

    # Periode selectionnee par famille via ?periode_<FAMILLE>=<id> (defaut "0" = en cours)
    today = date.today()

    stats_par_theme = {}
    totaux_famille = {}
    periodes_famille = {}
    periodes_json = {}
    periode_active = {}
    peut_reset = {}
    all_alertes = []
    historique = []

    for famille in sorted(familles):
        periodes = _periodes_famille(famille, db)
        periodes_famille[famille] = periodes
        sel_id = (request.query_params.get("periode_" + famille) or "0").strip()
        sel = next((p for p in periodes if p["id"] == sel_id), periodes[0])
        periode_active[famille] = sel["id"]

        th_stats, alertes, total = _build_stats(famille, sel["debut"], sel["fin"], db)
        stats_par_theme[famille] = th_stats
        totaux_famille[famille] = total
        all_alertes.extend(alertes)
        historique.extend(_build_historique(famille, db))

        # garde-fou reset : autorise uniquement le jour de l'audit externe
        peut_reset[famille] = (_config and _config.audit_externe_date == today)

        # version JSON-safe des periodes (pour le filtrage JS de l'historique commun)
        periodes_json[famille] = [
            {
                "id": p["id"],
                "label": p["label"],
                "debut": p["debut"].isoformat() if p["debut"] else None,
                "fin": p["fin"].isoformat() if p["fin"] else None,
            }
            for p in periodes
        ]

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

    annees_historique = sorted(
        {h["date_tirage"].year for h in historique if h.get("date_tirage")},
        reverse=True
    )

    return templates.TemplateResponse(
        request=request,
        name="statistiques.html",
        context={
            "stats_par_theme": stats_par_theme,
            "totaux_famille": totaux_famille,
            "theme_noms": THEME_NOMS,
            "alertes": all_alertes,
            "historique": historique,
            "annees_historique": annees_historique,
            "recap_occurrences": recap_occurrences,
            "periodes_famille": periodes_famille,
            "periodes_json": periodes_json,
            "periode_active": periode_active,
            "peut_reset": peut_reset,
        }
    )



@router.post("/statistiques/reset")
def reinitialiser_compteurs(
    payload: dict = Body(...),
    db: DBSession = Depends(get_db),
):
    """Cree un reset de compteurs pour une famille. Trois verrous :
    1) la date d'audit externe doit etre AUJOURD'HUI (jour exact) ;
    2) PIN administrateur valide ;
    3) la confirmation explicite est exigee cote front avant l'appel.
    Aucune donnee n'est supprimee : on ajoute seulement une borne datee."""
    famille = (payload.get("famille") or "").strip()
    pin = (payload.get("pin") or "").strip()

    if not famille:
        raise HTTPException(status_code=400, detail="Famille manquante.")

    # Verrou 1 : audit externe == aujourd'hui
    config = db.query(ConfigOrganisme).first()
    today = date.today()
    if not config or config.audit_externe_date != today:
        raise HTTPException(
            status_code=403,
            detail="Réinitialisation impossible : la date du jour ne correspond pas "
                   "à votre prochain audit externe. Modifiez votre date d'audit dans "
                   "Administration → Calendrier qualité.",
        )

    # Verrou 2 : PIN admin
    if pin != get_pin_admin(db):
        raise HTTPException(status_code=403, detail="Code PIN administrateur incorrect.")

    # Creation de la borne de reset (aucune suppression de donnees)
    reset = ResetTirage(famille=famille, date_reset=datetime.now())
    db.add(reset)
    db.commit()

    return {
        "ok": True,
        "famille": famille,
        "date_reset": reset.date_reset.strftime("%d/%m/%Y"),
    }