"""
migrate_phase2.py
Migration base de données pour le tirage par thème (Phase 2).
Compatible SQLite (local) et PostgreSQL (Railway).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from sqlalchemy import text, inspect


def run():
    db = SessionLocal()
    try:
        print("=== Migration Phase 2 — Tirage par thème ===\n")

        inspector = inspect(engine)
        dialect = engine.dialect.name
        print(f"Base de données : {dialect}\n")

        # 1. Table utilisations_themes
        print("1. Création table utilisations_themes...")
        tables = inspector.get_table_names()
        if "utilisations_themes" not in tables:
            db.execute(text("""
                CREATE TABLE utilisations_themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    famille VARCHAR(10) NOT NULL,
                    theme INTEGER NOT NULL,
                    grille_id INTEGER NOT NULL REFERENCES grilles_theorie(id),
                    annee INTEGER NOT NULL,
                    UNIQUE (session_id, famille, theme)
                )
            """) if dialect == "sqlite" else text("""
                CREATE TABLE utilisations_themes (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    famille VARCHAR(10) NOT NULL,
                    theme INTEGER NOT NULL,
                    grille_id INTEGER NOT NULL REFERENCES grilles_theorie(id),
                    annee INTEGER NOT NULL,
                    CONSTRAINT uq_session_famille_theme 
                        UNIQUE (session_id, famille, theme)
                )
            """))
            print("   ✅ utilisations_themes créée")
        else:
            print("   ✅ utilisations_themes déjà présente")

        # 2. Colonne tirage_themes_json sur jours_test
        print("2. Ajout colonne tirage_themes_json sur jours_test...")
        colonnes = [c["name"] for c in inspector.get_columns("jours_test")]
        if "tirage_themes_json" not in colonnes:
            db.execute(text(
                "ALTER TABLE jours_test ADD COLUMN tirage_themes_json TEXT"
            ))
            print("   ✅ tirage_themes_json ajoutée")
        else:
            print("   ✅ tirage_themes_json déjà présente")

        db.commit()
        print("\n✅ Migration terminée avec succès.")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur migration : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()