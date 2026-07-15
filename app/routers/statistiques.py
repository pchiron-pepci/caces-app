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


def _regime_periode(famille, debut, fin, db):
    """Regime fige de la periode : lit le mode_tirage d'un tirage de la periode.
    Defaut v2_grille si aucun tirage (periode vide -> on presume le referentiel courant)."""
    fp = _filtre_periode(debut, fin)
    q = db.query(UtilisationTheme.mode_tirage).filter(UtilisationTheme.famille == famille)
    if fp is not None:
        q = q.filter(fp)
    row = q.filter(UtilisationTheme.mode_tirage.isnot(None)).first()
    return row[0] if row else "v2_grille"


def _build_stats_v2(famille, debut, fin, db):
    """Regime grille complete : compte des SESSIONS DISTINCTES par grille.
    Retourne (liste_grilles, total_sessions, sous_seuil_7)."""
    grilles = (
        db.query(GrilleTheorie)
        .filter(GrilleTheorie.famille == famille, GrilleTheorie.actif == True)
        .order_by(GrilleTheorie.numero)
        .all()
    )
    fp = _filtre_periode(debut, fin)
    q = db.query(
        UtilisationTheme.grille_id,
        func.count(func.distinct(UtilisationTheme.session_id)),
    ).filter(
        UtilisationTheme.famille == famille,
        UtilisationTheme.mode_tirage == "v2_grille",
    )
    if fp is not None:
        q = q.filter(fp)
    usage = {gid: cnt for gid, cnt in q.group_by(UtilisationTheme.grille_id).all()}
    total = sum(usage.values())
    lignes = []
    for g in grilles:
        count = usage.get(g.id, 0)
        pct = round(count / total * 100) if total > 0 else 0
        if count == 0:
            statut = "VIDE"
        elif pct < 10:
            statut = "SOUS"
        elif pct > 30:
            statut = "SUR"
        else:
            statut = "OK"
        lignes.append({
            "grille_numero": g.numero,
            "grille_id": g.id,
            "count": count,
            "pct": pct,
            "statut": statut,
        })
    sous_seuil_7 = total < 7
    return lignes, total, sous_seuil_7


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


# ===================================================================
# Onglets "Tests & CDT" et "Testeurs" - calculs (filtre = annee de session)
# ===================================================================
def _annees_tests(db):
    from app.models.session_epreuve import SessionEpreuve
    from app.models.jour_test import ResultatTheorie
    annees = set()
    for (a,) in (db.query(SessionModel.annee)
                 .join(SessionEpreuve, SessionEpreuve.session_id == SessionModel.id)
                 .filter(SessionEpreuve.bloque == False).distinct().all()):
        if a: annees.add(a)
    for (a,) in (db.query(SessionModel.annee)
                 .join(ResultatTheorie, ResultatTheorie.session_id == SessionModel.id)
                 .filter(ResultatTheorie.bloque == False, ResultatTheorie.dispense == False)
                 .distinct().all()):
        if a: annees.add(a)
    return sorted(annees, reverse=True)


def _stats_pratique_famille_cat(annee, db):
    from app.models.session_epreuve import SessionEpreuve
    from app.models.lieu import Lieu
    # bucket par defaut = CDT (lieu inconnu ou lieu_id absent -> cdt), identique a _stats_par_testeur
    lieu_type = {l.id: (l.type or "cdt") for l in db.query(Lieu).all()}
    # Population = TOUTES les epreuves non bloquees (PAS de filtre testeur_id) :
    # garantit CDT + Hors == Passes. Ecart assume avec l'onglet Testeurs (voir CLAUDE.md).
    q = (db.query(SessionEpreuve.famille, SessionEpreuve.categorie, SessionEpreuve.obtenue,
                  SessionModel.lieu_id)
         .join(SessionModel, SessionModel.id == SessionEpreuve.session_id)
         .filter(SessionEpreuve.bloque == False))
    if annee is not None:
        q = q.filter(SessionModel.annee == annee)
    agg = {}
    for fam, cat, obtenue, lieu_id in q.all():
        k = (fam, cat)
        if k not in agg: agg[k] = [0, 0, 0, 0]  # passes, reussis, cdt, hors
        agg[k][0] += 1
        if obtenue: agg[k][1] += 1
        if lieu_type.get(lieu_id) == "hors_cdt": agg[k][3] += 1
        else: agg[k][2] += 1
    familles = {}
    tg_pass = tg_reu = tg_cdt = tg_hors = 0
    for (fam, cat), (p, r, cdt, hors) in sorted(agg.items()):
        familles.setdefault(fam, {"cats": [], "sous_total": [0, 0, 0, 0]})
        familles[fam]["cats"].append({"cat": cat, "passes": p, "reussis": r,
            "echoues": p - r, "pct": round(100 * r / p) if p else 0,
            "cdt": cdt, "hors": hors,
            "pct_hors": round(100 * hors / (cdt + hors)) if (cdt + hors) else 0})
        familles[fam]["sous_total"][0] += p
        familles[fam]["sous_total"][1] += r
        familles[fam]["sous_total"][2] += cdt
        familles[fam]["sous_total"][3] += hors
        tg_pass += p; tg_reu += r; tg_cdt += cdt; tg_hors += hors
    for fam, d in familles.items():
        sp, sr, scdt, shors = d["sous_total"]
        d["sous_total"] = {"passes": sp, "reussis": sr, "echoues": sp - sr,
                           "pct": round(100 * sr / sp) if sp else 0,
                           "cdt": scdt, "hors": shors,
                           "pct_hors": round(100 * shors / (scdt + shors)) if (scdt + shors) else 0}
    total_general = {"passes": tg_pass, "reussis": tg_reu, "echoues": tg_pass - tg_reu,
                     "pct": round(100 * tg_reu / tg_pass) if tg_pass else 0,
                     "cdt": tg_cdt, "hors": tg_hors,
                     "pct_hors": round(100 * tg_hors / (tg_cdt + tg_hors)) if (tg_cdt + tg_hors) else 0}
    return familles, total_general


def _stats_theorie_famille(annee, db):
    from app.models.jour_test import ResultatTheorie
    q = (db.query(SessionModel.famille, ResultatTheorie.obtenue)
         .join(ResultatTheorie, ResultatTheorie.session_id == SessionModel.id)
         .filter(ResultatTheorie.bloque == False, ResultatTheorie.dispense == False))
    if annee is not None:
        q = q.filter(SessionModel.annee == annee)
    agg = {}
    for fam, obtenue in q.all():
        if fam not in agg: agg[fam] = [0, 0]
        agg[fam][0] += 1
        if obtenue: agg[fam][1] += 1
    lignes = []
    tp = tr = 0
    for fam, (p, r) in sorted(agg.items()):
        lignes.append({"famille": fam, "passes": p, "reussis": r, "echoues": p - r,
                       "pct": round(100 * r / p) if p else 0})
        tp += p; tr += r
    total = {"passes": tp, "reussis": tr, "echoues": tp - tr,
             "pct": round(100 * tr / tp) if tp else 0}
    return lignes, total


def _stats_caces_delivres(annee, db):
    from app.models.caces_obtenu import CacesObtenu
    q = (db.query(CacesObtenu.famille, CacesObtenu.categorie)
         .join(SessionModel, SessionModel.id == CacesObtenu.session_id)
         .filter(CacesObtenu.statut == "valide",
                 CacesObtenu.organisme_externe.is_(None),
                 CacesObtenu.sous_traitance == False))
    if annee is not None:
        q = q.filter(SessionModel.annee == annee)
    agg = {}
    for fam, cat in q.all():
        agg[(fam, cat)] = agg.get((fam, cat), 0) + 1
    familles = {}
    total = 0
    for (fam, cat), n in sorted(agg.items()):
        familles.setdefault(fam, {"cats": [], "sous_total": 0})
        familles[fam]["cats"].append({"cat": cat, "nb": n})
        familles[fam]["sous_total"] += n
        total += n
    return familles, total


def _assembler_tableau_principal(annee, db):
    prat_fam, prat_tot = _stats_pratique_famille_cat(annee, db)
    theo_lignes, _ = _stats_theorie_famille(annee, db)
    caces_fam, caces_tot = _stats_caces_delivres(annee, db)
    theo_par_fam = {t["famille"]: t for t in theo_lignes}
    caces_cat = {}
    caces_st = {}
    for fam, d in caces_fam.items():
        caces_st[fam] = d["sous_total"]
        for c in d["cats"]:
            caces_cat[(fam, c["cat"])] = c["nb"]
    familles_set = set(prat_fam) | set(theo_par_fam) | set(caces_fam)
    familles = []
    for fam in sorted(familles_set):
        pd = prat_fam.get(fam, {"cats": [], "sous_total": {"passes":0,"reussis":0,"echoues":0,"pct":0,"cdt":0,"hors":0,"pct_hors":0}})
        cats = []
        for c in pd["cats"]:
            cats.append({**c, "caces": caces_cat.get((fam, c["cat"]), 0)})
        st = dict(pd["sous_total"])
        st["caces"] = caces_st.get(fam, 0)
        familles.append({"famille": fam, "theorie": theo_par_fam.get(fam),
                         "cats": cats, "sous_total": st})
    total = dict(prat_tot)
    total["caces"] = caces_tot
    return {"familles": familles, "total": total}


def _stats_par_testeur(annee, db):
    from app.models.session_epreuve import SessionEpreuve
    from app.models.jour_test import ResultatTheorie
    from app.models.testeur import Testeur
    from app.models.lieu import Lieu
    lieu_type = {l.id: (l.type or "cdt") for l in db.query(Lieu).all()}
    qth = (db.query(ResultatTheorie.testeur_id, SessionModel.famille, ResultatTheorie.obtenue)
           .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
           .filter(ResultatTheorie.bloque == False, ResultatTheorie.dispense == False,
                   ResultatTheorie.testeur_id.isnot(None)))
    if annee is not None:
        qth = qth.filter(SessionModel.annee == annee)
    theo = {}
    for tid, fam, obt in qth.all():
        k = (tid, fam)
        if k not in theo: theo[k] = [0, 0]
        theo[k][0] += 1
        if obt: theo[k][1] += 1
    qpr = (db.query(SessionEpreuve.testeur_id, SessionEpreuve.famille, SessionEpreuve.categorie,
                    SessionEpreuve.obtenue, SessionModel.lieu_id)
           .join(SessionModel, SessionModel.id == SessionEpreuve.session_id)
           .filter(SessionEpreuve.bloque == False, SessionEpreuve.testeur_id.isnot(None)))
    if annee is not None:
        qpr = qpr.filter(SessionModel.annee == annee)
    prat = {}
    for tid, fam, cat, obt, lieu_id in qpr.all():
        k = (tid, fam, cat)
        if k not in prat: prat[k] = {"passes": 0, "reussis": 0, "cdt": 0, "hors": 0}
        prat[k]["passes"] += 1
        if obt: prat[k]["reussis"] += 1
        if lieu_type.get(lieu_id) == "hors_cdt": prat[k]["hors"] += 1
        else: prat[k]["cdt"] += 1
    tids = {k[0] for k in theo} | {k[0] for k in prat}
    if not tids:
        return []
    testeurs = {t.id: t for t in db.query(Testeur).filter(Testeur.id.in_(tids)).all()}
    resultat = []
    for tid in tids:
        t = testeurs.get(tid)
        nom = f"{t.prenom} {t.nom}" if t else f"Testeur #{tid}"
        th_lignes = []
        tp = tr = 0
        for (xtid, fam), (p, r) in sorted(theo.items()):
            if xtid != tid: continue
            th_lignes.append({"famille": fam, "passes": p, "reussis": r, "echoues": p - r,
                              "pct": round(100 * r / p) if p else 0})
            tp += p; tr += r
        th_total = {"passes": tp, "reussis": tr, "echoues": tp - tr,
                    "pct": round(100 * tr / tp) if tp else 0}
        pr_lignes = []
        pp = pr_ = pcdt = phors = 0
        for (xtid, fam, cat), d in sorted(prat.items()):
            if xtid != tid: continue
            tot = d["cdt"] + d["hors"]
            pr_lignes.append({"famille": fam, "categorie": cat, "passes": d["passes"],
                              "reussis": d["reussis"], "echoues": d["passes"] - d["reussis"],
                              "pct": round(100 * d["reussis"] / d["passes"]) if d["passes"] else 0,
                              "cdt": d["cdt"], "hors": d["hors"],
                              "pct_hors": round(100 * d["hors"] / tot) if tot else 0})
            pp += d["passes"]; pr_ += d["reussis"]; pcdt += d["cdt"]; phors += d["hors"]
        ptot = pcdt + phors
        pr_total = {"passes": pp, "reussis": pr_, "echoues": pp - pr_,
                    "pct": round(100 * pr_ / pp) if pp else 0,
                    "cdt": pcdt, "hors": phors,
                    "pct_hors": round(100 * phors / ptot) if ptot else 0}
        resultat.append({"id": tid, "nom": nom, "theorie": th_lignes, "theo_total": th_total,
                         "pratique": pr_lignes, "prat_total": pr_total,
                         "nb_total": tp + pp, "pct_hors": pr_total["pct_hors"]})
    resultat.sort(key=lambda x: x["nom"].lower())
    return resultat


def _stats_formation(annee, db):
    from app.models.jour_formation import JourFormation, AffectationFormation
    from app.models.utilisateur import Utilisateur
    q = (db.query(AffectationFormation.user_id, SessionModel.famille, JourFormation.id)
         .join(JourFormation, JourFormation.id == AffectationFormation.jour_formation_id)
         .join(SessionModel, SessionModel.id == JourFormation.session_id)
         .filter(JourFormation.actif == True))
    if annee is not None:
        q = q.filter(SessionModel.annee == annee)
    seen = set()
    agg = {}
    familles_set = set()
    for uid, fam, jid in q.all():
        key = (uid, jid)
        if key in seen:
            continue
        seen.add(key)
        agg[(uid, fam)] = agg.get((uid, fam), 0) + 1
        familles_set.add(fam)
    familles = sorted(familles_set)
    uids = {u for (u, _) in agg}
    if not uids:
        return {"familles": [], "formateurs": [], "totaux": {}, "total": 0}
    users = {u.id: u for u in db.query(Utilisateur).filter(Utilisateur.id.in_(uids)).all()}
    formateurs = []
    totaux = {f: 0 for f in familles}
    total = 0
    for uid in uids:
        u = users.get(uid)
        nom = f"{u.prenom} {u.nom}" if u else f"Utilisateur #{uid}"
        par_fam = {}
        t = 0
        for f in familles:
            n = agg.get((uid, f), 0)
            par_fam[f] = n
            totaux[f] += n
            t += n
        formateurs.append({"nom": nom, "par_fam": par_fam, "total": t})
        total += t
    formateurs.sort(key=lambda x: x["nom"].lower())
    return {"familles": familles, "formateurs": formateurs, "totaux": totaux, "total": total}


@router.get("/statistiques", response_class=HTMLResponse)
async def page_statistiques(request: Request, db: DBSession = Depends(get_db), annee_tests: str = None):
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
    periodes_heterogene = {}
    regime_famille = {}
    stats_v2_famille = {}
    all_alertes = []
    historique = []

    for famille in sorted(familles):
        periodes = _periodes_famille(famille, db)
        # regime de chaque periode bornee (hors entree "tout")
        regimes_periodes = set()
        for _p in periodes:
            if _p["id"] == "tout":
                continue
            _p["regime"] = _regime_periode(famille, _p["debut"], _p["fin"], db)
            regimes_periodes.add(_p["regime"])
        heterogene = len(regimes_periodes) > 1
        # marquer l'entree "tout" indisponible si melange de regimes
        for _p in periodes:
            if _p["id"] == "tout":
                _p["indisponible"] = heterogene
                if heterogene:
                    _p["label"] = "Tout l'historique — indisponible (modes de tirage differents selon les periodes)"
        periodes_heterogene[famille] = heterogene
        periodes_famille[famille] = periodes
        sel_id = (request.query_params.get("periode_" + famille) or "0").strip()
        # garde-fou : refuser "tout" force par URL quand les regimes different -> periode en cours
        if sel_id == "tout" and heterogene:
            sel_id = "0"
        sel = next((p for p in periodes if p["id"] == sel_id), periodes[0])
        periode_active[famille] = sel["id"]

        th_stats, alertes, total = _build_stats(famille, sel["debut"], sel["fin"], db)
        stats_par_theme[famille] = th_stats
        totaux_famille[famille] = total
        all_alertes.extend(alertes)
        historique.extend(_build_historique(famille, db))

        # garde-fou reset : autorise uniquement le jour de l'audit externe
        peut_reset[famille] = (_config and _config.audit_externe_date == today)

        # regime fige de la periode + stats par grille si v2
        regime_famille[famille] = _regime_periode(famille, sel["debut"], sel["fin"], db)
        if regime_famille[famille] == "v2_grille":
            lignes_v2, total_v2, sous7 = _build_stats_v2(famille, sel["debut"], sel["fin"], db)
            stats_v2_famille[famille] = {"lignes": lignes_v2, "total": total_v2, "sous_seuil_7": sous7}

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

    # -- Onglets "Tests & CDT" / "Testeurs" / "Formation" --
    annees_tests = _annees_tests(db)
    _today_year = date.today().year
    if annee_tests in (None, ""):
        annee_sel = _today_year
    elif annee_tests == "all":
        annee_sel = None
    else:
        try:
            annee_sel = int(annee_tests)
        except (TypeError, ValueError):
            annee_sel = _today_year
    tableau_principal = _assembler_tableau_principal(annee_sel, db)
    stats_testeurs = _stats_par_testeur(annee_sel, db)
    stats_formation = _stats_formation(annee_sel, db)

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
            "periodes_heterogene": periodes_heterogene,
            "regime_famille": regime_famille,
            "stats_v2_famille": stats_v2_famille,
            "tests_annees": annees_tests,
            "tests_annee_sel": ("all" if annee_sel is None else annee_sel),
            "tests_tableau": tableau_principal,
            "tests_testeurs": stats_testeurs,
            "tests_formation": stats_formation,
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