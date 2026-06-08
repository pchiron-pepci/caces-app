from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.jour_test import JourTest, ResultatTheorie
from app.models.session_epreuve import SessionEpreuve
from app.models.session import Session as SessionModel
from app.models.caces_obtenu import CacesObtenu


def _date_echeance(famille: str, date_obt: date) -> date:
    ans = 10 if famille == "R482" else 5
    try:
        return date(date_obt.year + ans, date_obt.month, date_obt.day) - timedelta(days=1)
    except ValueError:
        return date(date_obt.year + ans, 3, 1) - timedelta(days=1)


def _chercher_theorie_autre_session(db, stagiaire_id, session_id_pratique, famille, date_pratique, statut_filtre):
    """
    Cherche un ResultatTheorie.obtenue=True dans des sessions d'une famille donnée,
    autres que la session de pratique, avec contrainte ±12 mois par rapport à la pratique.
    statut_filtre : "ouvert" (statut != terminee) ou "terminee" (statut == terminee).
    """
    limite_avant = date_pratique - timedelta(days=365)
    limite_apres = date_pratique + timedelta(days=365)

    q = (
        db.query(ResultatTheorie)
        .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .filter(
            ResultatTheorie.stagiaire_id == stagiaire_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.session_id != session_id_pratique,
            SessionModel.famille == famille,
            JourTest.date >= limite_avant,
            JourTest.date <= limite_apres,
        )
    )
    if statut_filtre == "ouvert":
        q = q.filter(SessionModel.statut != "terminee")
    else:
        q = q.filter(SessionModel.statut == "terminee")

    return q.order_by(ResultatTheorie.id.asc()).first()


def calculer_et_synchroniser(db: Session) -> list:
    """
    Pour chaque épreuve pratique réussie, recherche une théorie réussie selon 3 priorités :
      1. Même session
      2. Autre session ouverte (statut != terminee), même famille, ±12 mois → continuité
      3. Autre session clôturée (statut == terminee), même famille, ±12 mois → extension

    Règles date_obtention :
      Cas 1 : théorie == pratique (même jour)      → date_obtention = date pratique
      Cas 2 : théorie < pratique                   → date_obtention = date pratique
      Cas 3 : théorie > pratique                   → date_obtention = date théorie
      Cas 4 : théorie issue session clôturée        → date_obtention = date pratique
                                                     date_echeance  = échéance du 1er CACES® validé
                                                     dans cette famille, sinon calcul normal
    """
    epreuves_ok = db.query(SessionEpreuve).filter(SessionEpreuve.obtenue == True).all()

    for ep in epreuves_ok:
        existing = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == ep.stagiaire_id,
            CacesObtenu.session_id == ep.session_id,
            CacesObtenu.categorie == ep.categorie,
        ).first()
        if existing:
            if existing.statut == "a_valider" and existing.options_obtenues != ep.options_obtenues:
                existing.options_obtenues = ep.options_obtenues
            continue

        # Priorité 1 : théorie dans la même session
        rt = db.query(ResultatTheorie).filter(
            ResultatTheorie.stagiaire_id == ep.stagiaire_id,
            ResultatTheorie.session_id == ep.session_id,
            ResultatTheorie.obtenue == True,
        ).order_by(ResultatTheorie.id.asc()).first()

        post_cloture = False

        # Priorité 2 : autre session ouverte, même famille (continuité)
        if not rt:
            rt = _chercher_theorie_autre_session(
                db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "ouvert"
            )

        # Priorité 3 : session clôturée, même famille (extension)
        if not rt:
            rt = _chercher_theorie_autre_session(
                db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "terminee"
            )
            if rt:
                post_cloture = True

        if not rt:
            continue

        jour_theo = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
        if not jour_theo or not jour_theo.date:
            continue

        date_theo = jour_theo.date
        date_prat = ep.date

        if post_cloture:
            # Cas 4 : extension — date_echeance = échéance du CACES® initial dans cette famille
            date_obtention = date_prat
            caces_initial = (
                db.query(CacesObtenu)
                .filter(
                    CacesObtenu.stagiaire_id == ep.stagiaire_id,
                    CacesObtenu.famille == ep.famille,
                    CacesObtenu.statut == "valide",
                )
                .order_by(CacesObtenu.date_echeance.asc())
                .first()
            )
            echeance = caces_initial.date_echeance if caces_initial else _date_echeance(ep.famille, date_obtention)
        elif date_theo <= date_prat:
            # Cas 1/2 : théorie avant ou même jour que pratique
            date_obtention = date_prat
            echeance = _date_echeance(ep.famille, date_obtention)
        else:
            # Cas 3 : théorie après pratique
            date_obtention = date_theo
            echeance = _date_echeance(ep.famille, date_obtention)

        co = CacesObtenu(
            stagiaire_id=ep.stagiaire_id,
            session_id=ep.session_id,
            famille=ep.famille,
            categorie=ep.categorie,
            options_obtenues=ep.options_obtenues,
            date_obtention=date_obtention,
            date_echeance=echeance,
            statut="a_valider",
        )
        db.add(co)

    db.commit()

    return (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut == "a_valider")
        .order_by(CacesObtenu.id.desc())
        .all()
    )
