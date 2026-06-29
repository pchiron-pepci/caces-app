"""
app/services/calcul_fiche_reco.py

Étape 1 de la fiche de recommandation : agrège, pour un candidat dans une session,
toutes ses épreuves ÉCHOUÉES (théorie + pratiques multi-catégories) avec :
- la cause détectée (théorie : thèmes sous moyenne ; pratique : total / thème / élimination),
- la durée de formation recommandée PAR DÉFAUT (ajustable ensuite par le testeur),
- le traitement des options PE/TC (incluse vs facultative).

Lecture seule. Aucune écriture. Ne décide rien : propose des valeurs par défaut.

Les durées/règles sont ISOLÉES dans ce module (constantes en tête) pour devenir
configurables en admin plus tard.
"""

from sqlalchemy.orm import Session as DBSession

from app.models.jour_test import JourTest, ResultatTheorie
from app.models.grille_pratique import SaisiePratique
from app.models.stagiaire import Stagiaire
from app.models.option_categorie import OptionCategorie
from app.services.calcul_pratique import calculer_saisie

# ── Paramètres par défaut (À TERME configurables en admin) ───────────────────
# Durées exprimées en HEURES. La durée totale est cumulée (pas de plafond figé).
HEURES_PAR_THEME_PRATIQUE = 1.5   # pratique : par thème qui compte (moyenne KO ou PE à 0)
HEURES_FAUTE_ELIMINATOIRE = 1.0   # pratique : +1h forfaitaire si >=1 faute éliminatoire
SEUIL_THEORIE = 50.0              # note_totale >= 50 -> durée courte, sinon longue
HEURES_THEORIE_COURTE = 2.0       # théorie : note >= 50
HEURES_THEORIE_LONGUE = 4.0       # théorie : note < 50

NOMS_THEMES_THEORIE = {
    1: "Connaissances générales",
    2: "Technologie et stabilité",
    3: "Exploitation",
    4: "Circulation",
    5: "Entretien",
}


def _fmt_heures(h):
    """Formate une durée en heures : '2 h', '1,5 h', '7,5 h'."""
    if h is None:
        return None
    if float(h) == int(h):
        return str(int(h)) + " h"
    return ("%.1f" % h).replace(".", ",") + " h"


def _charger_params(db):
    """Charge les paramètres de durée depuis ConfigOrganisme, avec fallback sur les constantes."""
    p = {
        "h_theme": HEURES_PAR_THEME_PRATIQUE,
        "h_elim": HEURES_FAUTE_ELIMINATOIRE,
        "seuil": SEUIL_THEORIE,
        "h_theo_courte": HEURES_THEORIE_COURTE,
        "h_theo_longue": HEURES_THEORIE_LONGUE,
    }
    try:
        from app.models.config_organisme import ConfigOrganisme
        cfg = db.query(ConfigOrganisme).first()
        if cfg:
            if cfg.reco_h_theme_pratique is not None:
                p["h_theme"] = cfg.reco_h_theme_pratique
            if cfg.reco_h_forfait_elim is not None:
                p["h_elim"] = cfg.reco_h_forfait_elim
            if cfg.reco_seuil_theorie is not None:
                p["seuil"] = cfg.reco_seuil_theorie
            if cfg.reco_h_theorie_courte is not None:
                p["h_theo_courte"] = cfg.reco_h_theorie_courte
            if cfg.reco_h_theorie_longue is not None:
                p["h_theo_longue"] = cfg.reco_h_theorie_longue
    except Exception:
        pass
    return p


def _duree_theorie_heures(note_totale, params=None):
    p = params or {}
    seuil = p.get("seuil", SEUIL_THEORIE)
    courte = p.get("h_theo_courte", HEURES_THEORIE_COURTE)
    longue = p.get("h_theo_longue", HEURES_THEORIE_LONGUE)
    if note_totale is not None and note_totale >= seuil:
        return courte
    return longue


def _duree_pratique_heures(nb_themes, a_elimination, params=None):
    """Durée = (h/thème) × nb thèmes qui comptent + forfait si >=1 faute éliminatoire."""
    p = params or {}
    h = nb_themes * p.get("h_theme", HEURES_PAR_THEME_PRATIQUE)
    if a_elimination:
        h += p.get("h_elim", HEURES_FAUTE_ELIMINATOIRE)
    return round(h, 2)


def _theorie_echec(rt: ResultatTheorie, params=None) -> dict:
    """Détail de l'échec théorique : thèmes sous la moyenne + durée par défaut."""
    themes_echoues = []
    oks = [rt.theme1_ok, rt.theme2_ok, rt.theme3_ok, rt.theme4_ok, rt.theme5_ok]
    for i, ok in enumerate(oks, start=1):
        if ok is False:
            themes_echoues.append({"numero": i, "libelle": NOMS_THEMES_THEORIE[i]})
    h = _duree_theorie_heures(rt.note_totale, params)
    return {
        "type": "theorie",
        "note_totale": rt.note_totale,
        "themes_echoues": themes_echoues,
        "duree_heures": h,
        "duree_label": _fmt_heures(h),
    }


def _pratique_echec(saisie: SaisiePratique, db: DBSession, famille: str, params=None) -> dict:
    """Détail de l'échec d'une catégorie pratique, regroupé PAR THÈME.
    Durée = HEURES_PAR_THEME_PRATIQUE × nombre de thèmes qui comptent.
    Un thème compte si : sa moyenne est insuffisante OU il contient un PE à 0.
    Sous chaque thème : on liste les PE à 0 et les PE sous leur moyenne (distingués)."""
    calc = calculer_saisie(saisie, db)
    base = calc.get("base") or {}
    base_reussie = bool(calc.get("base_reussie"))

    # PE regroupés par thème, avec détection 0 / sous-moyenne
    pe_par_theme = {}
    for pe in base.get("points_evaluation", []):
        th = pe.get("theme") or ""
        note = pe.get("note")
        bareme = pe.get("bareme") or 0
        lib = pe.get("libelle_chapeau") or ("PE " + str(pe.get("numero")))
        est_zero = (note == 0)
        sous_moyenne = (bareme > 0 and note is not None and note < (bareme / 2.0) and not est_zero)
        if th not in pe_par_theme:
            pe_par_theme[th] = []
        pe_par_theme[th].append({
            "libelle": lib, "numero": pe.get("numero"),
            "note": note, "bareme": bareme,
            "zero": est_zero, "sous_moyenne": sous_moyenne,
        })

    # statut "ok" de chaque thème (moyenne du thème)
    theme_moyenne_ok = {}
    for t in base.get("themes", []):
        theme_moyenne_ok[t["libelle"]] = bool(t.get("ok"))

    # construire les blocs thèmes "qui comptent"
    themes_blocs = []
    for th_lib, pes in pe_par_theme.items():
        moyenne_ok = theme_moyenne_ok.get(th_lib, True)
        a_pe_zero = any(pe["zero"] for pe in pes)
        compte = (not moyenne_ok) or a_pe_zero
        if not compte:
            continue
        # questions à rappeler : PE à 0 + PE sous moyenne
        pe_zero = [pe for pe in pes if pe["zero"]]
        pe_sous = [pe for pe in pes if pe["sous_moyenne"]]
        themes_blocs.append({
            "theme": th_lib,
            "moyenne_insuffisante": not moyenne_ok,
            "pe_zero": pe_zero,
            "pe_sous_moyenne": pe_sous,
        })

    nb_themes = len(themes_blocs)

    # fautes éliminatoires cochées
    elim_coches = base.get("eliminatoires_coches") or []
    fautes_eliminatoires = []
    for e in elim_coches:
        if isinstance(e, str):
            fautes_eliminatoires.append(e)
        elif isinstance(e, dict):
            fautes_eliminatoires.append(e.get("libelle") or e.get("critere") or str(e))
        else:
            fautes_eliminatoires.append(str(e))
    a_elimination = len(fautes_eliminatoires) > 0

    # options : facultative échouée (base OK) -> à repasser à part ; incluse -> catégorie entière
    options_a_repasser = []
    categorie_entiere_par_option = False
    for opt in calc.get("options", []):
        if opt.get("reussi_bloc"):
            continue
        code = opt.get("code_option")
        oc = db.query(OptionCategorie).filter(
            OptionCategorie.famille == famille,
            OptionCategorie.categorie == saisie.categorie,
            OptionCategorie.code_option == code,
        ).first()
        incluse = bool(oc and oc.incluse)
        if incluse:
            categorie_entiere_par_option = True
        else:
            options_a_repasser.append({"code_option": code, "libelle": opt.get("libelle") or code})

    categorie_echouee = (not base_reussie) or categorie_entiere_par_option

    # durée = 1,5h × nb thèmes + 1h forfaitaire si faute éliminatoire.
    # Si échec sans aucun thème ni élimination (total seul) -> au moins 1 thème.
    nb_pour_duree = nb_themes
    if categorie_echouee and nb_pour_duree == 0 and not a_elimination:
        nb_pour_duree = 1
    duree_h = _duree_pratique_heures(nb_pour_duree, a_elimination, params) if categorie_echouee else None

    return {
        "type": "pratique",
        "categorie": saisie.categorie,
        "categorie_echouee": categorie_echouee,
        "base_reussie": base_reussie,
        "themes_blocs": themes_blocs,
        "nb_themes": nb_themes,
        "fautes_eliminatoires": fautes_eliminatoires,
        "a_elimination": a_elimination,
        "duree_heures": duree_h,
        "duree_label": _fmt_heures(duree_h) if duree_h is not None else None,
        "options_a_repasser": options_a_repasser,
        "categorie_entiere_par_option": categorie_entiere_par_option,
        "observations": (saisie.observations or "").strip(),
        "justification_ecart": (saisie.justification_ecart or "").strip(),
    }


def calculer_fiche_reco(session_id: int, stagiaire_id: int, db: DBSession) -> dict:
    """
    Agrège les épreuves échouées d'un candidat dans une session.
    Renvoie un dict prêt à pré-remplir la fiche de recommandation.
    """
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()

    # session (reference, dates, famille) - toujours disponible
    from app.models.session import Session as SessionModel
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    famille = sess.famille if sess else ""
    _params = _charger_params(db)

    # jours de test de la session
    jours = db.query(JourTest).filter(JourTest.session_id == session_id).all()
    jt_ids = [j.id for j in jours]

    # ── Théorie ──
    theorie_echec = None
    theorie_obtenue = None
    rt = db.query(ResultatTheorie).filter(
        ResultatTheorie.session_id == session_id,
        ResultatTheorie.stagiaire_id == stagiaire_id,
    ).order_by(ResultatTheorie.id.desc()).first()
    if rt is not None:
        theorie_obtenue = bool(rt.obtenue)
        if rt.obtenue is False:
            theorie_echec = _theorie_echec(rt, _params)

    # ── Pratiques (multi-catégories) ──
    pratiques_echec = []
    pratiques_obtenues = []
    if jt_ids:
        saisies = db.query(SaisiePratique).filter(
            SaisiePratique.jour_test_id.in_(jt_ids),
            SaisiePratique.stagiaire_id == stagiaire_id,
            SaisiePratique.statut == "valide",
        ).all()
        # dédupliquer par catégorie : garder la plus récente (id max)
        par_cat = {}
        for s in saisies:
            if s.categorie not in par_cat or s.id > par_cat[s.categorie].id:
                par_cat[s.categorie] = s
        for s in par_cat.values():
            detail = _pratique_echec(s, db, famille, _params)
            if detail["categorie_echouee"] or detail["options_a_repasser"]:
                pratiques_echec.append(detail)
            else:
                pratiques_obtenues.append({"categorie": s.categorie})

    a_des_echecs = bool(theorie_echec) or any(p["categorie_echouee"] for p in pratiques_echec) \
        or any(p["options_a_repasser"] for p in pratiques_echec)

    obs_parts = []
    for p in pratiques_echec:
        morceaux = []
        if p.get("justification_ecart"):
            morceaux.append(p["justification_ecart"])
        if p.get("observations"):
            morceaux.append(p["observations"])
        if morceaux:
            obs_parts.append("[" + str(p["categorie"]) + "] " + " — ".join(morceaux))
    observations_testeur = "\n".join(obs_parts)

    # durée totale cumulée (théorie + toutes pratiques échouées)
    total_h = 0.0
    if theorie_echec and theorie_echec.get("duree_heures"):
        total_h += theorie_echec["duree_heures"]
    for p in pratiques_echec:
        if p.get("duree_heures"):
            total_h += p["duree_heures"]

    return {
        "candidat": {
            "nom": stagiaire.nom if stagiaire else "",
            "prenom": stagiaire.prenom if stagiaire else "",
            "date_naissance": stagiaire.date_naissance.isoformat() if stagiaire and stagiaire.date_naissance else None,
        },
        "session": {
            "reference": sess.reference if sess else None,
            "famille": famille,
            "date_theorie": sess.date_theorie.isoformat() if sess and sess.date_theorie else None,
            "date_pratique_debut": sess.date_pratique_debut.isoformat() if sess and sess.date_pratique_debut else None,
            "date_pratique_fin": sess.date_pratique_fin.isoformat() if sess and sess.date_pratique_fin else None,
            "categories_echouees": [p["categorie"] for p in pratiques_echec if p.get("categorie_echouee")],
        },
        "session_id": session_id,
        "theorie_obtenue": theorie_obtenue,
        "theorie_echec": theorie_echec,
        "pratiques_echec": pratiques_echec,
        "pratiques_obtenues": pratiques_obtenues,
        "a_des_echecs": a_des_echecs,
        "observations_testeur": observations_testeur,
        "duree_totale_heures": round(total_h, 2),
        "duree_totale_label": _fmt_heures(round(total_h, 2)) if total_h else None,
    }