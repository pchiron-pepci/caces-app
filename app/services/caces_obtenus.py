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
    Cherche un ResultatTheorie.obtenue=True hors de la session de pratique,
    même famille, abs(date_theo - date_prat) ≤ 365 jours.
    statut_filtre : "ouvert" (statut != terminee) ou "terminee".
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
            ResultatTheorie.bloque != True,
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

    return q.order_by(JourTest.date.desc(), ResultatTheorie.id.desc()).first()


def _calculer_pour_epreuve(ep: SessionEpreuve, db) -> dict | None:
    """
    Calcule date_obtention, date_echeance et post_cloture pour une épreuve pratique réussie.
    Retourne None si aucune théorie réussie n'est trouvée.

    Priorités de recherche théorie :
      1. Même session
      2. Autre session ouverte (statut != terminee), même famille, ±12 mois → continuité
      3. Autre session clôturée (statut == terminee), même famille, ±12 mois → extension

    Règles de calcul (appliquées dans cet ordre) :
      Cas 3 : théorie > pratique (TOUTES priorités, y compris extension)
                → date_obtention = date_theo
                → date_echeance = _date_echeance(famille, date_theo)
      Cas 1/2 : théorie ≤ pratique, non-extension
                → date_obtention = date_prat
                → date_echeance = _date_echeance(famille, date_prat)
      Cas 4 : extension (session clôturée, post_cloture=True) + théorie ≤ pratique
                → date_obtention = date_prat
                → date_echeance = date_echeance du 1er CacesObtenu valide (même famille), sinon calcul normal
    """
    rt = (
        db.query(ResultatTheorie)
        .join(JourTest, JourTest.id == ResultatTheorie.jour_test_id)
        .filter(
            ResultatTheorie.stagiaire_id == ep.stagiaire_id,
            ResultatTheorie.session_id == ep.session_id,
            ResultatTheorie.obtenue == True,
            ResultatTheorie.bloque != True,
        )
        .order_by(JourTest.date.desc(), ResultatTheorie.id.desc())
        .first()
    )

    post_cloture = False

    if not rt:
        rt = _chercher_theorie_autre_session(
            db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "ouvert"
        )

    if not rt:
        rt = _chercher_theorie_autre_session(
            db, ep.stagiaire_id, ep.session_id, ep.famille, ep.date, "terminee"
        )
        if rt:
            post_cloture = True

    if not rt:
        return None

    jour_theo = db.query(JourTest).filter(JourTest.id == rt.jour_test_id).first()
    if not jour_theo or not jour_theo.date:
        return None

    date_theo = jour_theo.date
    date_prat = ep.date

    if date_theo > date_prat:
        # Cas 3 : théorie après pratique (toutes priorités) → tout depuis date_theo
        date_obtention = date_theo
        echeance = _date_echeance(ep.famille, date_theo)
    elif post_cloture:
        # Cas 4 : extension + théorie ≤ pratique → date pratique, écheance = CACES® initial
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
    else:
        # Cas 1/2 : théorie ≤ pratique, non-extension → date pratique
        date_obtention = date_prat
        echeance = _date_echeance(ep.famille, date_prat)

    return {
        "date_obtention": date_obtention,
        "date_echeance": echeance,
        "options_obtenues": ep.options_obtenues,
        "post_cloture": post_cloture,
    }


def calculer_et_synchroniser(db: Session) -> list:
    """
    Pour chaque épreuve pratique réussie :
    - Si aucun CacesObtenu n'existe → crée un enregistrement 'a_valider'
    - Si un enregistrement 'a_valider' existe → recalcule et met à jour les dates
      (notamment si le statut d'une session de théorie a changé : terminee → mode extension)
    - Si statut valide/annule → ne touche pas

    Appelé automatiquement lors de la clôture d'une session.
    """
    epreuves_ok = db.query(SessionEpreuve).filter(
        SessionEpreuve.obtenue == True,
        SessionEpreuve.bloque != True,
    ).all()

    for ep in epreuves_ok:
        calc = _calculer_pour_epreuve(ep, db)

        existing = db.query(CacesObtenu).filter(
            CacesObtenu.stagiaire_id == ep.stagiaire_id,
            CacesObtenu.session_id == ep.session_id,
            CacesObtenu.categorie == ep.categorie,
        ).first()

        if existing:
            if existing.statut == "a_valider" and calc is not None:
                # Recalculer les dates en cas de changement (ex : session théorie clôturée)
                existing.date_obtention = calc["date_obtention"]
                existing.date_echeance = calc["date_echeance"]
                existing.options_obtenues = calc["options_obtenues"]
            elif existing.statut == "annule" and calc is not None:
                # Remise en a_valider automatique : les données source sont toujours valides
                existing.statut = "a_valider"
                existing.numero_ordre = None
                existing.date_obtention = calc["date_obtention"]
                existing.date_echeance = calc["date_echeance"]
                existing.options_obtenues = calc["options_obtenues"]
            continue

        if calc is None:
            continue

        db.add(CacesObtenu(
            stagiaire_id=ep.stagiaire_id,
            session_id=ep.session_id,
            famille=ep.famille,
            categorie=ep.categorie,
            options_obtenues=calc["options_obtenues"],
            date_obtention=calc["date_obtention"],
            date_echeance=calc["date_echeance"],
            statut="a_valider",
        ))

    db.commit()

    return (
        db.query(CacesObtenu)
        .filter(CacesObtenu.statut == "a_valider")
        .order_by(CacesObtenu.id.desc())
        .all()
    )
