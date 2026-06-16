"""
migrate_date_tirage.py
Ajoute la colonne date_tirage (TIMESTAMP nullable) sur utilisations_themes.
Idempotent : ne fait rien si la colonne existe déjà.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from sqlalchemy import text, inspect


def run():
    db = SessionLocal()
    try:
        dialect = engine.dialect.name
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("utilisations_themes")]

        if "date_tirage" in cols:
            print("✅ date_tirage déjà présente — rien à faire.")
            return

        print("Ajout colonne date_tirage sur utilisations_themes...")
        if dialect == "postgresql":
            db.execute(text(
                "ALTER TABLE utilisations_themes ADD COLUMN IF NOT EXISTS date_tirage TIMESTAMP"
            ))
        else:
            db.execute(text(
                "ALTER TABLE utilisations_themes ADD COLUMN date_tirage TIMESTAMP"
            ))
        db.commit()
        print("✅ date_tirage ajoutée.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
