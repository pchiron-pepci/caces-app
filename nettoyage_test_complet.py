"""
Script JETABLE - grand nettoyage des donnees de test.
Garde le referentiel pur, vide tout le reste (y compris testeurs, stagiaires, lieux).
A ne PAS confondre avec reset_donnees_of.py (outil client recurrent qui, lui, conserve
testeurs et stagiaires). Ce script-ci est un nettoyage ponctuel avant migration R2.

Lancement : python nettoyage_test_complet.py   (confirmation RESET requise)
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")

# Tables a vider. TRUNCATE CASCADE gere l'ordre des FK.
# Conserve (NON listees ici) : familles, categories, option_categorie,
# grilles_theorie, reponses_grilles, grille_pratique, theme_pratique,
# point_evaluation, item_pratique, critere_eliminatoire, config_organisme, utilisateurs.
TABLES_A_VIDER = [
    "sessions", "jours_test", "jour_test_candidats", "resultats_theorie",
    "brouillons_theorie", "session_candidats", "session_epreuves", "caces_obtenus",
    "carte_caces", "fiche_recommandation", "consentements_rgpd",
    "attestations_neutralite", "justificatifs", "non_conformites",
    "saisie_pratique", "saisie_bloc", "saisie_item_note", "saisie_eliminatoire",
    "jours_formation", "affectations_formation", "planning_apprenants", "affectations_test",
    "utilisations_grilles", "utilisations_themes", "reset_tirage", "equipements",
    "stagiaires", "testeurs", "habilitations_testeurs", "habilitation_option",
    "lieu_habilitations", "carte_testeur", "lieux", "document_officiel",
    "association_log", "association_audio_log",
]

def main():
    if DATABASE_URL.startswith("sqlite"):
        print("[!] DATABASE_URL pointe sur SQLite local. Es-tu sur la bonne base (prod) ?")
    engine = create_engine(DATABASE_URL)

    print("=== Lignes AVANT nettoyage ===")
    total = 0
    with engine.connect() as conn:
        for t in TABLES_A_VIDER:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            except Exception as e:
                print(f"  {t:28s} : absente ({type(e).__name__})")
                continue
            total += n
            print(f"  {t:28s} : {n}")
    print(f"  {'TOTAL':28s} : {total}")

    print("\n=== Lignes CONSERVEES (referentiel) ===")
    with engine.connect() as conn:
        for t in ["familles","categories","option_categorie","grilles_theorie",
                  "reponses_grilles","grille_pratique","config_organisme","utilisateurs"]:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"  {t:28s} : {n}")
            except Exception:
                pass

    if total == 0:
        print("\n[OK] Rien a supprimer, deja propre.")
        return

    print("\n>>> IRREVERSIBLE. Vide testeurs, stagiaires, lieux et toute la production.")
    if input(">>> Tape exactement RESET pour confirmer : ").strip() != "RESET":
        print("[ANNULE]")
        return

    liste = ", ".join(TABLES_A_VIDER)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {liste} RESTART IDENTITY CASCADE"))
    print("\n[OK] Nettoyage effectue. Referentiel conserve.")

    print("\n=== Verification APRES ===")
    with engine.connect() as conn:
        restant = 0
        for t in TABLES_A_VIDER:
            try:
                restant += conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            except Exception:
                pass
        print(f"  Lignes restantes dans les tables videes : {restant}")
        for t in ["familles","grilles_theorie","reponses_grilles","config_organisme","utilisateurs"]:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"  {t:28s} : {n} (conserve)")
            except Exception:
                pass

if __name__ == "__main__":
    main()
