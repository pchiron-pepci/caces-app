"""Moteur de calcul de l'evaluation pratique CACES.

Regle de reussite d'un bloc (base ou option) :
  1. note globale >= note_min (70/100 base, 35/50 option)
  2. ET chaque theme >= bareme_theme / 2 (valeur exacte)
  3. ET chaque PE > 0 (un point d'evaluation nul = echec direct)
  4. ET aucun critere eliminatoire coche
Le mode de saisie (binaire / partiel_entier / partiel_demi) determine les
notes atteignables : aucun arrondi n'est applique ici, on compare la valeur reelle.

Subordination : une option n'est ACQUISE que si elle reussit ET que la base reussit.

NORYX assiste : ce moteur PROPOSE un resultat. La decision reste au testeur.
"""
from app.models.grille_pratique import (
    GrillePratique, ThemePratique, PointEvaluation, ItemPratique,
    SaisieBloc, SaisieItemNote, SaisieEliminatoire, CritereEliminatoire,
)


def calculer_bloc(bloc: SaisieBloc, db) -> dict:
    """Calcule le resultat detaille d'UN bloc (base ou option). Ne tient pas
    compte de la subordination (gere au niveau de la saisie globale)."""
    grille = db.query(GrillePratique).filter(GrillePratique.id == bloc.grille_id).first()
    if not grille:
        raise ValueError("Grille introuvable pour le bloc %s" % bloc.id)

    notes = {n.item_id: (n.note if n.note is not None else 0.0)
             for n in db.query(SaisieItemNote).filter(SaisieItemNote.bloc_id == bloc.id).all()}

    note_globale = 0.0
    themes_detail = []
    pes_detail = []
    raisons = []
    tout_ok = True

    themes = db.query(ThemePratique).filter(
        ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre).all()

    for th in themes:
        note_theme = 0.0
        seuil_theme = th.bareme_theme / 2.0
        points = db.query(PointEvaluation).filter(
            PointEvaluation.theme_id == th.id).order_by(PointEvaluation.ordre).all()

        for pe in points:
            note_pe = 0.0
            bareme_pe = 0.0
            items = db.query(ItemPratique).filter(
                ItemPratique.pe_id == pe.id).all()
            for it in items:
                if it.bareme_max:
                    bareme_pe += it.bareme_max
                    note_pe += notes.get(it.id, 0.0)
            note_theme += note_pe
            # REGLE PE : un PE a 0 = echec direct (pris a l'envers : note_pe > 0 = OK).
            # Ce n'est PAS un seuil a la moitie (ca, c'est la regle des THEMES).
            pe_ok = note_pe > 0
            if not pe_ok:
                tout_ok = False
                raisons.append("PE %s ('%s') a 0 = echec (un point d'evaluation ne peut pas etre nul)" % (
                    pe.numero, th.libelle))
            pes_detail.append({
                "theme": th.libelle, "numero": pe.numero,
                "note": round(note_pe, 2), "bareme": round(bareme_pe, 2),
                "seuil": 0, "ok": pe_ok,
            })

        note_globale += note_theme
        theme_ok = note_theme >= seuil_theme
        if not theme_ok:
            tout_ok = False
            raisons.append("Theme '%s' : %s/%s < seuil %s" % (
                th.libelle, round(note_theme, 2), round(th.bareme_theme, 2), round(seuil_theme, 2)))
        themes_detail.append({
            "libelle": th.libelle, "note": round(note_theme, 2),
            "bareme": round(th.bareme_theme, 2), "seuil": round(seuil_theme, 2), "ok": theme_ok,
        })

    global_ok = note_globale >= grille.note_min
    if not global_ok:
        raisons.append("Note globale %s/%s < seuil %s" % (
            round(note_globale, 2), round(grille.note_max, 2), round(grille.note_min, 2)))

    elim_coches = db.query(SaisieEliminatoire).filter(
        SaisieEliminatoire.bloc_id == bloc.id).all()
    elim_detail = []
    for e in elim_coches:
        crit = db.query(CritereEliminatoire).filter(
            CritereEliminatoire.id == e.critere_id).first()
        elim_detail.append(crit.libelle if crit else "Critere %s" % e.critere_id)
    if elim_detail:
        raisons.append("Critere(s) eliminatoire(s) : " + " ; ".join(elim_detail))

    reussi = global_ok and tout_ok and (len(elim_detail) == 0)

    return {
        "grille_id": grille.id,
        "type": grille.type,
        "code_option": grille.code_option,
        "libelle": grille.libelle,
        "note_globale": round(note_globale, 2),
        "note_max": round(grille.note_max, 2),
        "note_min": round(grille.note_min, 2),
        "reussi": reussi,
        "themes": themes_detail,
        "points_evaluation": pes_detail,
        "eliminatoires_coches": elim_detail,
        "raisons_echec": raisons,
    }


def calculer_saisie(saisie, db) -> dict:
    """Calcule le resultat GLOBAL d'une saisie (base + options), avec subordination."""
    blocs = db.query(SaisieBloc).filter(SaisieBloc.saisie_id == saisie.id).all()

    res_base = None
    res_options = []
    for bloc in blocs:
        detail = calculer_bloc(bloc, db)
        if detail["type"] == "base":
            res_base = detail
            res_base["_bloc_id"] = bloc.id
        else:
            detail["_bloc_id"] = bloc.id
            res_options.append(detail)

    base_reussie = bool(res_base and res_base["reussi"])

    for opt in res_options:
        opt["reussi_bloc"] = opt["reussi"]
        opt["acquis"] = opt["reussi"] and base_reussie
        if opt["reussi"] and not base_reussie:
            opt["raisons_echec"].append(
                "Option non acquise : la categorie de base n'est pas obtenue.")

    return {
        "base": res_base,
        "options": res_options,
        "base_reussie": base_reussie,
        "categorie_acquise": base_reussie,
    }


def appliquer_resultats(saisie, db) -> dict:
    """Calcule ET ecrit la synthese dans les SaisieBloc. Ne touche pas a SessionEpreuve."""
    res = calculer_saisie(saisie, db)

    if res["base"]:
        b = db.query(SaisieBloc).filter(SaisieBloc.id == res["base"]["_bloc_id"]).first()
        if b:
            b.note_calculee = res["base"]["note_globale"]
            b.resultat_propose = res["base"]["reussi"]
            b.resultat_acquis = res["base"]["reussi"]

    for opt in res["options"]:
        b = db.query(SaisieBloc).filter(SaisieBloc.id == opt["_bloc_id"]).first()
        if b:
            b.note_calculee = opt["note_globale"]
            b.resultat_propose = opt["reussi_bloc"]
            b.resultat_acquis = opt["acquis"]

    db.commit()
    return res
