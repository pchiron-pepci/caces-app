"""
Remise a zero des donnees de production (OF) en conservant le referentiel.

CONSERVE : familles, categories, option_categorie, grilles theorie + questions,
grilles pratique (referentiel), config_organisme, document_officiel, utilisateurs,
lieux, stagiaires, testeurs + habilitations + cartes testeur, logs association.

VIDE : sessions, jours, candidats, resultats, CACES, cartes CACES, fiches reco,
consentements, neutralite, justificatifs, NC, saisies pratique, jours formation,
TIRAGES (utilisations grilles/themes, reset_tirage), equipements.

Lancement : python reset_donnees_of.py
"""
import os
import sys
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")

# Tables a vider. TRUNCATE CASCADE gere l'ordre des FK automatiquement.
# Aucune table conservee ne pointe vers ces tables (les FK vont du
# transactionnel vers le referentiel, jamais l'inverse) -> CASCADE sans danger.
TABLES_A_VIDER = [
    "sessions",
    "jours_test",
    "jour_test_candidats",
    "resultats_theorie",
    "brouillons_theorie",
    "session_candidats",
    "session_epreuves",
    "caces_obtenus",
    "carte_caces",
    "fiche_recommandation",
    "consentements_rgpd",
    "attestations_neutralite",
    "justificatifs",
    "non_conformites",
    "saisie_pratique",
    "saisie_bloc",
    "saisie_item_note",
    "saisie_eliminatoire",
    "jours_formation",
    "affectations_formation",
    "planning_apprenants",
    "affectations_test",
    "utilisations_grilles",
    "utilisations_themes",
    "reset_tirage",
    "equipements",
]

def main():
    if DATABASE_URL.startswith("sqlite"):
        print("[!] DATABASE_URL pointe sur SQLite local. Es-tu sur la bonne base ?")
    engine = create_engine(DATABASE_URL)

    # Comptage avant
    print("=== Lignes presentes AVANT reset ===")
    total = 0
    with engine.connect() as conn:
        for t in TABLES_A_VIDER:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            except Exception as e:
                print(f"  {t:28s} : table absente ({type(e).__name__})")
                continue
            total += n
            print(f"  {t:28s} : {n}")
    print(f"  {'TOTAL':28s} : {total}")

    if total == 0:
        print("\n[OK] Rien a supprimer, base deja propre.")
        return

    print("\n>>> Cette operation est IRREVERSIBLE.")
    rep = input(">>> Tape exactement RESET pour confirmer : ").strip()
    if rep != "RESET":
        print("[ANNULE] Aucune modification.")
        return

    # TRUNCATE en une transaction, RESTART IDENTITY remet les compteurs d'ID a 0
    liste = ", ".join(TABLES_A_VIDER)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {liste} RESTART IDENTITY CASCADE"))
    print("\n[OK] Donnees de production videes. Referentiel conserve.")

    # Verification apres
    print("\n=== Lignes presentes APRES reset ===")
    with engine.connect() as conn:
        for t in TABLES_A_VIDER:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"  {t:28s} : {n}")
            except Exception:
                pass

if __name__ == "__main__":
    main()
