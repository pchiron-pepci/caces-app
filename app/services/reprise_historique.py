from app.models.session import Session


def get_or_create_session_reprise(stagiaire_id: int, db) -> Session:
    """
    Recupere (ou cree) la session technique de reprise d'historique d'un candidat.
    Une seule par candidat, reutilisee. type='reprise' → invisible des listes operationnelles.
    """
    reference = "REPRISE-" + str(stagiaire_id)
    sess = db.query(Session).filter(
        Session.type == "reprise",
        Session.reference == reference,
    ).first()
    if sess:
        return sess
    sess = Session(
        famille="REPRISE",        # sentinelle ; les CacesObtenu repris portent leur vraie famille
        lieu_id=0,                # sentinelle (pas de FK sur lieu_id)
        reference=reference,
        statut="terminee",        # exclue des sessions actives
        type="reprise",           # exclue des listes via le filtre type != 'reprise'
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess
