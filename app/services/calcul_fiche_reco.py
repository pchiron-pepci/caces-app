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
HEURES_PAR_THEME_PRATIQUE = 1.5   # pratique : par thème échoué OU point d'évaluation à 0
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


def _duree_theorie_heures(note_totale):
    if note_totale is not None and note_totale >= SEUIL_THEORIE:
        return HEURES_THEORIE_COURTE
    return HEURES_THEORIE_LONGUE


def _duree_pratique_heures(nb_points_faibles):
    """nb_points_faibles = nb thèmes échoués + nb PE à 0. Cumul, sans plafond figé."""
    return round(max(nb_points_faibles, 1) * HEURES_PAR_THEME_PRATIQUE, 2)


def _theorie_echec(rt: ResultatTheorie) -> dict:
    """Détail de l'échec théorique : thèmes sous la moyenne + durée par défaut."""
    themes_echoues = []
    oks = [rt.theme1_ok, rt.theme2_ok, rt.theme3_ok, rt.theme4_ok, rt.theme5_ok]
    for i, ok in enumerate(oks, start=1):
        if ok is False:
            themes_echoues.append({"numero": i, "libelle": NOMS_THEMES_THEORIE[i]})
    h = _duree_theorie_heures(rt.note_totale)
    return {
        "type": "theorie",
        "note_totale": rt.note_totale,
        "themes_echoues": themes_echoues,
        "duree_heures": h,
        "duree_label": _fmt_heures(h),
    }


def _pratique_echec(saisie: SaisiePratique, db: DBSession, famille: str) -> dict:
    """Détail de l'échec d'une catégorie pratique : motifs cumulés + durée en heures."""
    calc = calculer_saisie(saisie, db)
    base = calc.get("base") or {}
    base_reussie = bool(calc.get("base_reussie"))

    # thèmes sous la moyenne
    themes_echoues = [t["libelle"] for t in base.get("themes", []) if not t.get("ok")]
    # points d'évaluation à 0 (un PE est ok=False uniquement quand sa note vaut 0)
    pe_zero = []
    for pe in base.get("points_evaluation", []):
        if not pe.get("ok"):
            lib = pe.get("libelle_chapeau") or ("PE " + str(pe.get("numero")))
            pe_zero.append({"theme": pe.get("theme"), "libelle": lib, "numero": pe.get("numero")})
    # critères éliminatoires cochés
    elim_coches = base.get("eliminatoires_coches") or []

    # liste des MOTIFS d'échec (cumul, pour affichage détaillé)
    motifs = []
    for t in themes_echoues:
        motifs.append("Thème sous la moyenne : " + t)
    for pe in pe_zero:
        motifs.append("Point d'évaluation à 0 : " + pe["libelle"])
    for e in elim_coches:
        lib = e if isinstance(e, str) else (e.get("libelle") if isinstance(e, dict) else str(e))
        motifs.append("Critère éliminatoire : " + str(lib))
    # cas total < 70 sans motif fin identifié
    if not base_reussie and not motifs:
        motifs.append("Total inférieur à 70/100")

    # nombre de points faibles pour la durée (thèmes échoués + PE à 0)
    nb_points_faibles = len(themes_echoues) + len(pe_zero)
    if nb_points_faibles == 0 and not base_reussie:
        nb_points_faibles = 1  # total insuffisant : au moins une unité de formation

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

    duree_h = _duree_pratique_heures(nb_points_faibles) if categorie_echouee else None

    return {
        "type": "pratique",
        "categorie": saisie.categorie,
        "categorie_echouee": categorie_echouee,
        "base_reussie": base_reussie,
        "motifs": motifs,
        "themes_echoues": themes_echoues,
        "pe_zero": pe_zero,
        "nb_points_faibles": nb_points_faibles,
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