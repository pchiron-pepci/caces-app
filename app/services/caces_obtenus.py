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
        # 29 fév → 28 fév de l'année cible
        return date(date_obt.year + ans, 3, 1) - timedelta(days=1)


def calculer_et_synchroniser(db: Session) -> list:
    """
    Pour chaque épreuve pratique réussie, vérifie qu'une théorie réussie existe
    et crée le CacesObtenu manquant en statut 'a_valider'.
    Retourne tous les enregistrements 'a_valider'.

    Règles date_obtention :
      Cas 1/2 : théorie ≤ pratique (même jour ou théorie avant) → date_obtention = date pratique
      Cas 3   : théorie > pratique → date_obtention = date théorie
      Cas 4   : théorie issue d'une autre session terminée (post-clôture)
                → date_obtention = date pratique
                → date_echeance  = échéance du premier CACES® validé dans cette famille,
                                   sinon calcul normal
    """
    epreuves_ok = db.query(SessionEpreuve).filter(SessionEpreuve.obtenue == True).all()

    for ep in epreuves_ok:
        existing = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == ep.stagiaire_id,
            CacesObtenu.session_id == ep.session_id,
            CacesObtenu.categorie == ep.categorie,
        ).first()
        if existing:
            continue

        # Théorie réussie dans la même session
        rt = db.query(ResultatTheorie).filter(
            ResultatTheorie.stagiaire_id == ep.stagiaire_id,
            ResultatTheorie.session_id == ep.session_id,
            ResultatTheorie.obtenue == True,
        ).order_by(ResultatTheorie.id.asc()).first()

        post_cloture = False
        if not rt:
            # Extension post-clôture : théorie d'une autre session terminée, même famille
            rt = (
                db.query(ResultatTheorie)
                .join(SessionModel, SessionModel.id == ResultatTheorie.session_id)
                .filter(
                    ResultatTheorie.stagiaire_id == ep.stagiaire_id,
                    ResultatTheorie.obtenue == True,
                    SessionModel.famille == ep.famille,
                    SessionModel.statut == "terminee",
                )
                .order_by(ResultatTheorie.id.asc())
                .first()
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
            # Cas 4
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
            # Cas 1 (même jour) ou Cas 2 (théorie avant pratique)
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
