"""
migrate_audio_question.py
Ajoute audio_url (VARCHAR 500) sur reponses_grilles.
Idempotent : skip si la colonne est déjà présente.
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
        cols = [c["name"] for c in inspector.get_columns("reponses_grilles")]

        if "audio_url" in cols:
            print("✅ audio_url déjà présente — skip.")
            return

        if dialect == "postgresql":
            sql = "ALTER TABLE reponses_grilles ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)"
        else:
            sql = "ALTER TABLE reponses_grilles ADD COLUMN audio_url VARCHAR(500)"

        print(f"Exécution : {sql}")
        db.execute(text(sql))
        db.commit()
        print("✅ Migration audio_question terminée.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
