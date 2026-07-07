"""
migrate_audio_url_f.py
Ajoute audio_url_f (VARCHAR 500) sur reponses_grilles = 2e voix (feminine).
audio_url reste la voix par defaut (masculine/H), audio_url_f = voix feminine (F).
Idempotent : skip si la colonne est deja presente.
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

        if "audio_url_f" in cols:
            print("audio_url_f deja presente - skip.")
            return

        if dialect == "postgresql":
            sql = "ALTER TABLE reponses_grilles ADD COLUMN IF NOT EXISTS audio_url_f VARCHAR(500)"
        else:
            sql = "ALTER TABLE reponses_grilles ADD COLUMN audio_url_f VARCHAR(500)"

        print(f"Execution : {sql}")
        db.execute(text(sql))
        db.commit()
        print("OK Migration audio_url_f terminee.")
    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
