"""
check_questions.py — verification READ-ONLY de reponses_grilles (R482)
Aucune ecriture en base. Uniquement des SELECT.

Commande Render Shell :
  python check_questions.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille
from init_questions_r482 import GRILLES_R482, POINTS_THEME, get_image_url

# Attendus par theme (derives de GRILLES_R482 grille 1, representatif)
ATTENDUS_THEME = {
    grille_num: {
        theme_num: len(questions)
        for theme_num, questions in themes.items()
    }
    for grille_num, themes in GRILLES_R482.items()
}
ATTENDU_TOTAL = 100
FAMILLE = "R482"
NB_GRILLES = 5

anomalies = 0


def section(titre):
    print(f"\n{'=' * 60}")
    print(f"  {titre}")
    print('=' * 60)


def ok(msg):
    print(f"  OK  {msg}")


def warn(msg):
    global anomalies
    anomalies += 1
    print(f"  !!  {msg}")


def run():
    db = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # Charger les grilles R482
        # ------------------------------------------------------------------
        grilles = (
            db.query(GrilleTheorie)
            .filter(GrilleTheorie.famille == FAMILLE)
            .order_by(GrilleTheorie.numero)
            .all()
        )
        grille_map = {g.numero: g for g in grilles}

        # ------------------------------------------------------------------
        # 1. COMPLETUDE
        # ------------------------------------------------------------------
        section("1. COMPLETUDE")

        if set(grille_map.keys()) != set(range(1, NB_GRILLES + 1)):
            manquantes = set(range(1, NB_GRILLES + 1)) - set(grille_map.keys())
            superflues = set(grille_map.keys()) - set(range(1, NB_GRILLES + 1))
            if manquantes:
                warn(f"Grilles manquantes dans grilles_theorie : {sorted(manquantes)}")
            if superflues:
                warn(f"Grilles inattendues dans grilles_theorie : {sorted(superflues)}")
        else:
            ok(f"{NB_GRILLES} grilles R482 presentes (numeros 1-{NB_GRILLES})")

        for grille_num in range(1, NB_GRILLES + 1):
            if grille_num not in grille_map:
                continue
            g = grille_map[grille_num]
            total_grille = 0
            details = []
            for theme_num in range(1, 6):
                attendu = ATTENDUS_THEME[grille_num][theme_num]
                compte = (
                    db.query(ReponseGrille)
                    .filter(
                        ReponseGrille.grille_id == g.id,
                        ReponseGrille.theme == theme_num,
                    )
                    .count()
                )
                total_grille += compte
                if compte != attendu:
                    details.append(f"T{theme_num}={compte}/{attendu}")
            if total_grille == ATTENDU_TOTAL and not details:
                ok(f"Grille {grille_num} (id={g.id}) : {total_grille}/{ATTENDU_TOTAL} questions")
            else:
                warn(
                    f"Grille {grille_num} (id={g.id}) : {total_grille}/{ATTENDU_TOTAL}"
                    + (f" — ecarts par theme : {', '.join(details)}" if details else "")
                )

        # ------------------------------------------------------------------
        # 2. INTEGRITE BASE vs SOURCE
        # ------------------------------------------------------------------
        section("2. INTEGRITE BASE vs SOURCE (init_questions_r482.py)")

        ecarts_integrite = 0

        for grille_num, themes in GRILLES_R482.items():
            if grille_num not in grille_map:
                warn(f"Grille {grille_num} absente de la base, controle ignore")
                continue
            g = grille_map[grille_num]

            # Charger toutes les questions de cette grille en base, indexees
            rows = db.query(ReponseGrille).filter(ReponseGrille.grille_id == g.id).all()
            db_index = {(r.theme, r.numero_question): r for r in rows}
            db_keys_vus = set()

            for theme_num, questions in themes.items():
                for (q_num, texte_src, rep_src) in questions:
                    cle = (theme_num, q_num)
                    db_keys_vus.add(cle)
                    if cle not in db_index:
                        warn(f"G{grille_num} T{theme_num} Q{q_num} — MANQUANTE en base")
                        ecarts_integrite += 1
                        continue
                    r = db_index[cle]
                    champs_ko = []
                    if r.texte_question != texte_src:
                        champs_ko.append(
                            f"texte_question:\n"
                            f"      base='{r.texte_question}'\n"
                            f"      src ='{texte_src}'"
                        )
                    if r.reponse_correcte != rep_src:
                        champs_ko.append(
                            f"reponse_correcte: base={r.reponse_correcte} src={rep_src}"
                        )
                    pts_attendus = POINTS_THEME[theme_num]
                    if r.points != pts_attendus:
                        champs_ko.append(
                            f"points: base={r.points} src={pts_attendus}"
                        )
                    img_attendue = get_image_url(grille_num, theme_num, q_num)
                    if r.image_url != img_attendue:
                        champs_ko.append(
                            f"image_url: base='{r.image_url}' src='{img_attendue}'"
                        )
                    if champs_ko:
                        warn(f"G{grille_num} T{theme_num} Q{q_num} — divergence : {'; '.join(champs_ko)}")
                        ecarts_integrite += 1

            # Questions en base absentes de la source
            for cle in db_index:
                if cle not in db_keys_vus:
                    warn(f"G{grille_num} T{cle[0]} Q{cle[1]} — EN BASE mais absente de la source")
                    ecarts_integrite += 1

        if ecarts_integrite == 0:
            ok("Toutes les questions correspondent exactement a la source")

        # ------------------------------------------------------------------
        # 3. VALIDITE METIER
        # ------------------------------------------------------------------
        section("3. VALIDITE METIER")

        all_rows = (
            db.query(ReponseGrille)
            .join(GrilleTheorie, ReponseGrille.grille_id == GrilleTheorie.id)
            .filter(GrilleTheorie.famille == FAMILLE)
            .all()
        )

        # 3a. reponse_correcte hors domaine (domaine = True/False)
        hors_domaine = [
            r for r in all_rows if not isinstance(r.reponse_correcte, bool)
        ]
        if hors_domaine:
            for r in hors_domaine:
                warn(
                    f"reponse_correcte hors domaine (bool attendu) : "
                    f"grille_id={r.grille_id} T{r.theme} Q{r.numero_question} "
                    f"valeur={r.reponse_correcte!r}"
                )
        else:
            ok("reponse_correcte : toutes les valeurs sont des booleens")

        # 3b. Doublons (grille_id, theme, numero_question)
        seen = {}
        doublons = []
        for r in all_rows:
            cle = (r.grille_id, r.theme, r.numero_question)
            if cle in seen:
                doublons.append((cle, seen[cle], r.id))
            else:
                seen[cle] = r.id
        if doublons:
            for (cle, id1, id2) in doublons:
                warn(
                    f"Doublon (grille_id={cle[0]}, T{cle[1]}, Q{cle[2]}) "
                    f"ids={id1} et {id2}"
                )
        else:
            ok("Doublons : aucun")

        # 3c. texte_question vide ou nul
        textes_ko = [
            r for r in all_rows
            if not r.texte_question or not r.texte_question.strip()
        ]
        if textes_ko:
            for r in textes_ko:
                warn(
                    f"texte_question vide/nul : "
                    f"grille_id={r.grille_id} T{r.theme} Q{r.numero_question}"
                )
        else:
            ok("texte_question : aucun vide ni nul")

        # 3d. points incoherents avec POINTS_THEME
        points_ko = [
            r for r in all_rows
            if r.theme in POINTS_THEME and r.points != POINTS_THEME[r.theme]
        ]
        if points_ko:
            for r in points_ko:
                warn(
                    f"points incoherent : grille_id={r.grille_id} T{r.theme} Q{r.numero_question} "
                    f"points={r.points} attendu={POINTS_THEME[r.theme]}"
                )
        else:
            ok("points : tous coherents avec POINTS_THEME")

        # 3e. image_url nulle ou vide
        img_ko = [
            r for r in all_rows
            if not r.image_url or not r.image_url.strip()
        ]
        if img_ko:
            for r in img_ko:
                warn(
                    f"image_url vide/nulle : "
                    f"grille_id={r.grille_id} T{r.theme} Q{r.numero_question}"
                )
        else:
            ok("image_url : aucune vide ni nulle")

        # ------------------------------------------------------------------
        # STATUT GLOBAL
        # ------------------------------------------------------------------
        section("STATUT GLOBAL")
        total_rows = len(all_rows)
        print(f"  {total_rows} enregistrements analyses dans reponses_grilles (R482)")
        if anomalies == 0:
            print("\n  OK  Tout est coherent — aucune anomalie detectee.")
        else:
            print(f"\n  !!  {anomalies} anomalie(s) detectee(s) — voir details ci-dessus.")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    run()
