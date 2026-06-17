from datetime import date as date_type


def statut_affichage_session(
    session,
    a_tirage: bool,
    a_epreuve: bool,
    a_resultat_theorie: bool,
    today: date_type = None,
) -> str:
    if today is None:
        today = date_type.today()

    if session.statut == "terminee":
        return "Clôturée"

    fin = session.date_pratique_fin
    if fin is not None and fin < today and a_tirage and not a_epreuve and not a_resultat_theorie:
        return "À réutiliser"

    return "Ouverte"
