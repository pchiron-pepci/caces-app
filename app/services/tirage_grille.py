import random
from sqlalchemy.orm import Session
from app.models.grille_theorie import GrilleTheorie, UtilisationGrille

def tirer_grille(famille: str, session_id: int, annee: int, db: Session) -> GrilleTheorie:
    """
    Tire aléatoirement une grille pour une session en respectant
    la contrainte 10%-30% d'utilisation par grille.
    """
    # 1. Récupérer toutes les grilles actives de la famille
    grilles = db.query(GrilleTheorie).filter(
        GrilleTheorie.famille == famille,
        GrilleTheorie.actif == True
    ).all()

    if not grilles:
        raise ValueError(f"Aucune grille disponible pour la famille {famille}")

    # 2. Compter le total de sessions de l'année
    total_sessions = db.query(UtilisationGrille).filter(
        UtilisationGrille.annee == annee
    ).count()

    # 3. Calculer le % d'utilisation de chaque grille
    stats = {}
    for g in grilles:
        count = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == g.id,
            UtilisationGrille.annee == annee
        ).count()
        pct = (count / total_sessions * 100) if total_sessions > 0 else 0
        stats[g.id] = {"grille": g, "count": count, "pct": pct}

    # 4. Catégoriser les grilles
    sous_utilisees = [s["grille"] for s in stats.values() if s["pct"] < 10]
    ok = [s["grille"] for s in stats.values() if 10 <= s["pct"] <= 30]
    sur_utilisees = [s["grille"] for s in stats.values() if s["pct"] > 30]

    # 5. Tirage avec priorité
    if sous_utilisees:
        # Priorité aux grilles sous-utilisées
        grille_choisie = random.choice(sous_utilisees)
        raison = f"sous-utilisée ({stats[grille_choisie.id]['pct']:.0f}%)"
    elif ok:
        # Tirage normal parmi les grilles ok
        grille_choisie = random.choice(ok)
        raison = f"dans les limites ({stats[grille_choisie.id]['pct']:.0f}%)"
    else:
        # Toutes sur-utilisées, on prend la moins utilisée
        grille_choisie = min(stats.values(), key=lambda x: x["count"])["grille"]
        raison = f"moins utilisée ({stats[grille_choisie.id]['pct']:.0f}%)"

    # 6. Enregistrer l'utilisation
    utilisation = UtilisationGrille(
        grille_id=grille_choisie.id,
        session_id=session_id,
        annee=annee
    )
    db.add(utilisation)
    db.commit()

    print(f"Grille R482 n°{grille_choisie.numero} tirée ({raison})")
    return grille_choisie


def get_stats_grilles(famille: str, annee: int, db: Session) -> list:
    """
    Retourne les statistiques d'utilisation des grilles pour une famille.
    """
    grilles = db.query(GrilleTheorie).filter(
        GrilleTheorie.famille == famille,
        GrilleTheorie.actif == True
    ).all()

    total_sessions = db.query(UtilisationGrille).filter(
        UtilisationGrille.annee == annee
    ).count()

    result = []
    for g in grilles:
        count = db.query(UtilisationGrille).filter(
            UtilisationGrille.grille_id == g.id,
            UtilisationGrille.annee == annee
        ).count()
        pct = (count / total_sessions * 100) if total_sessions > 0 else 0
        statut = "OK"
        if pct < 10:
            statut = "SOUS-UTILISEE"
        elif pct > 30:
            statut = "SUR-UTILISEE"
        result.append({
            "grille_id": g.id,
            "numero": g.numero,
            "count": count,
            "pct": round(pct, 1),
            "statut": statut
        })

    return result


def calculer_resultat_theorie(reponses_candidat: dict, grille_id: int, db: Session) -> dict:
    """
    Calcule le résultat théorique d'un candidat.
    reponses_candidat = {theme: [True/False, ...]}
    Retourne les notes par thème, note totale et obtention.
    """
    from app.models.grille_theorie import ReponseGrille

    reponses_grille = db.query(ReponseGrille).filter(
        ReponseGrille.grille_id == grille_id
    ).order_by(ReponseGrille.theme, ReponseGrille.numero_question).all()

    # Points max par thème
    points_max = {}
    for r in reponses_grille:
        if r.theme not in points_max:
            points_max[r.theme] = 0
        points_max[r.theme] += r.points

    # Calculer notes
    notes_theme = {}
    for r in reponses_grille:
        theme = r.theme
        q_idx = r.numero_question - 1
        if theme not in notes_theme:
            notes_theme[theme] = 0
        # Vérifier si la réponse du candidat est correcte
        candidat_reponses = reponses_candidat.get(str(theme), [])
        if q_idx < len(candidat_reponses):
            reponse = candidat_reponses[q_idx]
            if reponse is not None and reponse == r.reponse_correcte:
                notes_theme[theme] += r.points

    note_totale = sum(notes_theme.values())

    # Vérifier seuils par thème (>= moyenne de chaque thème)
    themes_ok = {}
    for theme, note in notes_theme.items():
        max_theme = points_max.get(theme, 0)
        moyenne_theme = max_theme / 2
        themes_ok[theme] = note >= moyenne_theme

    obtenue = note_totale >= 70 and all(themes_ok.values())

    return {
        "note_totale": round(note_totale),
        "notes_themes": {str(t): round(n) for t, n in notes_theme.items()},
        "points_max_themes": {str(t): round(p) for t, p in points_max.items()},
        "themes_ok": {str(t): v for t, v in themes_ok.items()},
        "obtenue": obtenue
    }