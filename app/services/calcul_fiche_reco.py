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
DUREES_THEORIE = {
    "courte": "Théorie en groupe - 3 heures minimum",
    "longue": "Théorie en groupe - 6 heures minimum",
    "indef": "Théorie en groupe - Durée indéfinissable",
}
DUREES_PRATIQUE = {
    1: "Pratique individuelle - 1 heure minimum (1 exercice)",
    2: "Pratique individuelle - 2 heures minimum (plusieurs exercices)",
    4: "Pratique individuelle - 4 heures minimum (plusieurs exercices)",
    6: "Pratique individuelle - 6 heures minimum (plusieurs exercices)",
}
SEUIL_THEORIE_COURTE = 50.0   # note_totale >= 50 -> 3h, sinon 6h
HEURES_PAR_THEME = 2          # pratique total<70 : 2h par thème échoué
PLAFOND_PRATIQUE_H = 6        # plafonné à 6h
HEURES_ELIMINATION = 2        # élimination sur un point -> 2h

NOMS_THEMES_THEORIE = {
    1: "Connaissances générales",
    2: "Technologie et stabilité",
    3: "Exploitation",
    4: "Circulation",
    5: "Entretien",
}


def _duree_theorie_defaut(note_totale):
    if note_totale is not None and note_totale >= SEUIL_THEORIE_COURTE:
        return DUREES_THEORIE["courte"]
    return DUREES_THEORIE["longue"]


def _duree_pratique_defaut(nb_themes_echoues, elimination):
    if elimination:
        h = HEURES_ELIMINATION
    else:
        h = min(max(nb_themes_echoues, 1) * HEURES_PAR_THEME, PLAFOND_PRATIQUE_H)
    # arrondir à une durée existante (1,2,4,6)
    if h <= 1:
        h = 1
    elif h <= 2:
        h = 2
    elif h <= 4:
        h = 4
    else:
        h = 6
    return DUREES_PRATIQUE[h]


def _theorie_echec(rt: ResultatTheorie) -> dict:
    """Détail de l'échec théorique : thèmes sous la moyenne + durée par défaut."""
    themes_echoues = []
    oks = [rt.theme1_ok, rt.theme2_ok, rt.theme3_ok, rt.theme4_ok, rt.theme5_ok]
    for i, ok in enumerate(oks, start=1):
        if ok is False:
            themes_echoues.append({"numero": i, "libelle": NOMS_THEMES_THEORIE[i]})
    return {
        "type": "theorie",
        "note_totale": rt.note_totale,
        "themes_echoues": themes_echoues,
        "duree_defaut": _duree_theorie_defaut(rt.note_totale),
        "durees_possibles": list(DUREES_THEORIE.values()),
    }


def _pratique_echec(saisie: SaisiePratique, db: DBSession, famille: str) -> dict:
    """Détail de l'échec d'une catégorie pratique : cause + durée + options."""
    calc = calculer_saisie(saisie, db)
    base = calc.get("base") or {}
    base_reussie = bool(calc.get("base_reussie"))

    # thèmes échoués de la base
    themes_echoues = [t["libelle"] for t in base.get("themes", []) if not t.get("ok")]
    # élimination = un PE à 0 ou un éliminatoire coché
    pe_zero = any(not pe.get("ok") for pe in base.get("points_evaluation", []))
    elim_coches = bool(base.get("eliminatoires_coches"))
    elimination = pe_zero or elim_coches

    # cause principale
    if not base_reussie:
        if elimination:
            cause = "elimination"
            cause_label = "Élimination sur un point d'évaluation"
        elif themes_echoues:
            cause = "theme"
            cause_label = "Moyenne d'un thème insuffisante"
        else:
            cause = "total"
            cause_label = "Total inférieur à 70/100"
    else:
        cause = None
        cause_label = None

    # options : facultative échouée (base OK) -> à repasser à part ; incluse -> catégorie entière
    options_a_repasser = []
    categorie_entiere_par_option = False
    for opt in calc.get("options", []):
        if opt.get("reussi_bloc"):
            continue  # option réussie
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

    # la catégorie est "échouée" si base ratée OU option incluse ratée
    categorie_echouee = (not base_reussie) or categorie_entiere_par_option

    return {
        "type": "pratique",
        "categorie": saisie.categorie,
        "categorie_echouee": categorie_echouee,
        "base_reussie": base_reussie,
        "cause": cause,
        "cause_label": cause_label,
        "themes_echoues": themes_echoues,
        "elimination": elimination,
        "duree_defaut": _duree_pratique_defaut(len(themes_echoues), elimination) if categorie_echouee else None,
        "durees_possibles": list(DUREES_PRATIQUE.values()),
        "options_a_repasser": options_a_repasser,
        "categorie_entiere_par_option": categorie_entiere_par_option,
        "observations": (saisie.observations or "").strip(),
    }


def calculer_fiche_reco(session_id: int, stagiaire_id: int, db: DBSession) -> dict:
    """
    Agrège les épreuves échouées d'un candidat dans une session.
    Renvoie un dict prêt à pré-remplir la fiche de recommandation.
    """
    stagiaire = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()

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
            theorie_echec = _theorie_echec(rt)

    # ── Pratiques (multi-catégories) ──
    pratiques_echec = []
    pratiques_obtenues = []
    if jt_ids:
        saisies = db.query(SaisiePratique).filter(
            SaisiePratique.jour_test_id.in_(jt_ids),
            SaisiePratique.stagiaire_id == stagiaire_id,
            SaisiePratique.statut == "valide",
        ).all()
        # déterminer la famille via la session
        from app.models.session import Session as SessionModel
        sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        famille = sess.famille if sess else ""
        # dédupliquer par catégorie : garder la plus récente (id max)
        par_cat = {}
        for s in saisies:
            if s.categorie not in par_cat or s.id > par_cat[s.categorie].id:
                par_cat[s.categorie] = s
        for s in par_cat.values():
            detail = _pratique_echec(s, db, famille)
            if detail["categorie_echouee"] or detail["options_a_repasser"]:
                pratiques_echec.append(detail)
            else:
                pratiques_obtenues.append({"categorie": s.categorie})

    a_des_echecs = bool(theorie_echec) or any(p["categorie_echouee"] for p in pratiques_echec) \
        or any(p["options_a_repasser"] for p in pratiques_echec)

    obs_parts = []
    for p in pratiques_echec:
        obs = p.get("observations")
        if obs:
            obs_parts.append("[" + str(p["categorie"]) + "] " + obs)
    observations_testeur = "\n".join(obs_parts)

    return {
        "candidat": {
            "nom": stagiaire.nom if stagiaire else "",
            "prenom": stagiaire.prenom if stagiaire else "",
            "date_naissance": stagiaire.date_naissance.isoformat() if stagiaire and stagiaire.date_naissance else None,
        },
        "session_id": session_id,
        "theorie_obtenue": theorie_obtenue,
        "theorie_echec": theorie_echec,
        "pratiques_echec": pratiques_echec,
        "pratiques_obtenues": pratiques_obtenues,
        "a_des_echecs": a_des_echecs,
        "observations_testeur": observations_testeur,
    }