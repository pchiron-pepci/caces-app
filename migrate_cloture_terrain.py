"""
migrate_cloture_terrain.py
Ajoute la colonne date_cloture_terrain (TIMESTAMP nullable) sur sessions.
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
        cols = [c["name"] for c in inspector.get_columns("sessions")]

        if "date_cloture_terrain" in cols:
            print("✅ date_cloture_terrain déjà présente — rien à faire.")
            return

        print("Ajout colonne date_cloture_terrain sur sessions...")
        if dialect == "postgresql":
            db.execute(text(
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS date_cloture_terrain TIMESTAMP"
            ))
        else:
            db.execute(text(
                "ALTER TABLE sessions ADD COLUMN date_cloture_terrain TIMESTAMP"
            ))
        db.commit()
        print("✅ date_cloture_terrain ajoutée.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
