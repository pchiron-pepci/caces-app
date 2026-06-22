"""
app/services/tirage_grille.py
Phase 2 INRS (applicable jan 2029) : tirage aléatoire par thème.
Phase 1 conservée intacte pour les sessions existantes.
"""

import random
import json
from collections import defaultdict
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille
from app.models.utilisations_themes import UtilisationTheme


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Tirage par thème
# ═══════════════════════════════════════════════════════════════════════════════

def get_themes_famille(famille: str, db: DBSession) -> list[int]:
    rows = (
        db.query(ReponseGrille.theme)
        .join(GrilleTheorie)
        .filter(GrilleTheorie.famille == famille, GrilleTheorie.actif == True)
        .distinct()
        .order_by(ReponseGrille.theme)
        .all()
    )
    return [r[0] for r in rows]


def get_grilles_famille(famille: str, db: DBSession) -> list[GrilleTheorie]:
    return (
        db.query(GrilleTheorie)
        .filter(GrilleTheorie.famille == famille, GrilleTheorie.actif == True)
        .order_by(GrilleTheorie.numero)
        .all()
    )


def tirer_themes_phase2(famille: str, session_id: int, annee: int, db: DBSession) -> dict:
    # Compteur minimum strict, par thème indépendamment.
    # Source de vérité : historique global (utilisations_themes), sans filtre annee.
    # Tirage aléatoire parmi les ex-aequo au compteur minimum.
    grilles = get_grilles_famille(famille, db)
    if not grilles:
        raise ValueError(f"Aucune grille active pour la famille {famille}")

    themes = get_themes_famille(famille, db)
    if not themes:
        raise ValueError(f"Aucun thème trouvé pour la famille {famille}")

    rows = (
        db.query(
            UtilisationTheme.theme,
            UtilisationTheme.grille_id,
            func.count(UtilisationTheme.id).label("cnt")
        )
        .filter(UtilisationTheme.famille == famille)
        .group_by(UtilisationTheme.theme, UtilisationTheme.grille_id)
        .all()
    )
    compteurs = defaultdict(lambda: defaultdict(int))
    for theme, grille_id, cnt in rows:
        compteurs[theme][grille_id] = cnt

    grille_ids = [g.id for g in grilles]
    grille_by_id = {g.id: g for g in grilles}

    tirage = {}
    for theme in themes:
        counts = {g_id: compteurs[theme].get(g_id, 0) for g_id in grille_ids}
        min_count = min(counts.values())
        candidats = [g_id for g_id, c in counts.items() if c == min_count]
        tirage[theme] = grille_by_id[random.choice(candidats)]

    return tirage


def enregistrer_tirage_themes(session_id: int, famille: str, annee: int, tirage: dict, db: DBSession, date_tirage=None, declenche_par_id=None) -> None:
    for theme, grille in tirage.items():
        existing = (
            db.query(UtilisationTheme)
            .filter(
                UtilisationTheme.session_id == session_id,
                UtilisationTheme.famille == famille,
                UtilisationTheme.theme == theme
            )
            .first()
        )
        if existing:
            existing.grille_id = grille.id
            existing.annee = annee
            if date_tirage:
                existing.date_tirage = date_tirage
            if declenche_par_id:
                existing.declenche_par_id = declenche_par_id
        else:
            db.add(UtilisationTheme(
                session_id=session_id,
                famille=famille,
                theme=theme,
                grille_id=grille.id,
                annee=annee,
                date_tirage=date_tirage,
                declenche_par_id=declenche_par_id,
            ))
    db.commit()


def get_questions_phase2(session_id: int, famille: str, db: DBSession) -> dict:
    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.session_id == session_id,
            UtilisationTheme.famille == famille
        )
        .order_by(UtilisationTheme.theme)
        .all()
    )
    if not tirages:
        raise ValueError(f"Aucun tirage Phase 2 trouvé pour session {session_id}")

    themes_data = {}
    tirage_resume = {}

    for ut in tirages:
        grille = db.query(GrilleTheorie).filter(GrilleTheorie.id == ut.grille_id).first()
        questions = (
            db.query(ReponseGrille)
            .filter(
                ReponseGrille.grille_id == ut.grille_id,
                ReponseGrille.theme == ut.theme
            )
            .order_by(ReponseGrille.numero_question)
            .all()
        )
        themes_data[ut.theme] = [
            {
                "numero": q.numero_question,
                "points": q.points,
                "texte": q.texte_question,
                "image": q.image_url,
                "audio": q.audio_url,
                "grille_id": ut.grille_id,
            }
            for q in questions
        ]
        tirage_resume[ut.theme] = {
            "grille_id": ut.grille_id,
            "grille_numero": grille.numero if grille else None,
        }

    return {"tirage": tirage_resume, "themes": themes_data}


def calculer_resultat_theorie_phase2(reponses: dict, session_id: int, famille: str, db: DBSession) -> dict:
    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.session_id == session_id,
            UtilisationTheme.famille == famille
        )
        .all()
    )
    if not tirages:
        raise ValueError(f"Aucun tirage Phase 2 pour session {session_id}")

    notes_themes = {}
    max_themes = {}
    themes_ok = {}
    note_totale = 0.0
    max_total = 0.0

    for ut in tirages:
        questions = (
            db.query(ReponseGrille)
            .filter(
                ReponseGrille.grille_id == ut.grille_id,
                ReponseGrille.theme == ut.theme
            )
            .order_by(ReponseGrille.numero_question)
            .all()
        )
        note_theme = 0.0
        max_theme = sum(q.points for q in questions)

        for q in questions:
            key = str(ut.theme) + "_" + str(q.numero_question)
            rep = reponses.get(key, None)
            if rep is not None and rep == q.reponse_correcte:
                note_theme += q.points

        max_total += max_theme
        note_totale += note_theme

        t_str = str(ut.theme)
        notes_themes[t_str] = round(note_theme, 1)
        max_themes[t_str] = round(max_theme, 1)
        themes_ok[t_str] = note_theme >= (max_theme / 2)

    pct_total = (note_totale / max_total * 100) if max_total else 0
    obtenue = pct_total >= 70 and all(themes_ok.values())

    return {
        "note_totale": round(note_totale, 1),
        "max_total": round(max_total, 1),
        "pct_total": round(pct_total, 1),
        "notes_themes": notes_themes,
        "max_themes": max_themes,
        "themes_ok": themes_ok,
        "obtenue": obtenue,
    }


def get_tirage_session(session_id: int, famille: str, db: DBSession) -> dict:
    tirages = (
        db.query(UtilisationTheme)
        .filter(
            UtilisationTheme.session_id == session_id,
            UtilisationTheme.famille == famille
        )
        .all()
    )
    return {t.theme: t.grille_id for t in tirages}


def tirage_to_json(tirage: dict) -> str:
    return json.dumps({str(t): g.numero for t, g in tirage.items()})


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Conservée intacte pour sessions existantes
# ═══════════════════════════════════════════════════════════════════════════════

def tirer_grille(famille: str, session_id: int, annee: int, db: DBSession) -> GrilleTheorie:
    grilles = (
        db.query(GrilleTheorie)
        .filter(GrilleTheorie.famille == famille, GrilleTheorie.actif == True)
        .all()
    )
    if not grilles:
        raise ValueError(f"Aucune grille pour {famille}")

    usages = (
        db.query(UtilisationGrille.grille_id, func.count(UtilisationGrille.id))
        .filter(UtilisationGrille.annee == annee)
        .group_by(UtilisationGrille.grille_id)
        .all()
    )
    usage_map = {g_id: cnt for g_id, cnt in usages}
    total = sum(usage_map.values()) or 1

    scored = []
    for g in grilles:
        taux = usage_map.get(g.id, 0) / total
        scored.append((abs(taux - 0.20), random.random(), g))

    scored.sort(key=lambda x: (x[0], x[1]))
    choisie = scored[0][2]

    db.add(UtilisationGrille(
        grille_id=choisie.id,
        session_id=session_id,
        annee=annee
    ))
    db.commit()
    return choisie


def calculer_resultat_theorie(reponses: dict, grille_id: int, db: DBSession) -> dict:
    questions = (
        db.query(ReponseGrille)
        .filter(ReponseGrille.grille_id == grille_id)
        .all()
    )
    notes_themes = defaultdict(float)
    max_themes = defaultdict(float)

    for q in questions:
        t = str(q.theme)
        max_themes[t] += q.points
        rep = reponses.get(str(q.numero_question), None)
        if rep is not None and rep == q.reponse_correcte:
            notes_themes[t] += q.points

    themes_ok = {t: notes_themes[t] >= (max_themes[t] / 2) for t in max_themes}
    note_totale = sum(notes_themes.values())
    max_total = sum(max_themes.values())
    pct = (note_totale / max_total * 100) if max_total else 0
    obtenue = pct >= 70 and all(themes_ok.values())

    return {
        "note_totale": round(note_totale, 1),
        "notes_themes": {t: round(v, 1) for t, v in notes_themes.items()},
        "themes_ok": themes_ok,
        "obtenue": obtenue,
    }