from app.models.session import Session


def get_or_create_session_reprise(stagiaire_id: int, db, famille: str = "REPRISE") -> Session:
    """
    Recupere (ou cree) la session technique de reprise d'un candidat.
    - famille="REPRISE" (defaut) : session sentinelle pour les CACES COMPLETS repris (H2). Reference REPRISE-{stag}.
    - famille=<reelle> (R489...) : session receptacle des ORPHELINES de cette famille (H3/H4). Reference REPRISE-{stag}-{famille}. Session.famille = famille reelle → le moteur la detecte par famille.
    type='reprise' → invisible des listes operationnelles.
    """
    if famille == "REPRISE":
        reference = "REPRISE-" + str(stagiaire_id)
    else:
        reference = "REPRISE-" + str(stagiaire_id) + "-" + famille
    sess = db.query(Session).filter(
        Session.type == "reprise",
        Session.reference == reference,
    ).first()
    if sess:
        return sess
    sess = Session(
        famille=famille,
        lieu_id=0,
        reference=reference,
        statut="terminee",
        type="reprise",
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess
