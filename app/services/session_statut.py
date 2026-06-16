from datetime import date as date_type


def statut_affichage_session(
    session,
    nb_candidats_actifs: int,
    a_grille_theorie: bool,
    a_epreuve: bool,
    a_resultat_theorie: bool,
    today: date_type = None,
) -> str:
    if today is None:
        today = date_type.today()

    fin = session.date_pratique_fin

    # Fin non dépassée (NULL ou >= aujourd'hui)
    if fin is None or fin >= today:
        return "Ouverte" if nb_candidats_actifs > 0 else "À planifier"

    # Fin dépassée
    if a_grille_theorie and not a_epreuve and not a_resultat_theorie:
        return "À reprendre"
    if session.statut == "terminee":
        return "Clôturée"
    return "À traiter"
