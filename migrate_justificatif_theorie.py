"""
migrate_justificatif_theorie.py
Ajoute justificatif_pdf (TEXT) et justificatif_nom (VARCHAR 255) sur
resultats_theorie.
Idempotent : skip les colonnes déjà présentes.
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
        cols = [c["name"] for c in inspector.get_columns("resultats_theorie")]

        migrations = []
        if "justificatif_pdf" not in cols:
            if dialect == "postgresql":
                migrations.append(
                    "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS justificatif_pdf TEXT"
                )
            else:
                migrations.append(
                    "ALTER TABLE resultats_theorie ADD COLUMN justificatif_pdf TEXT"
                )
        else:
            print("✅ justificatif_pdf déjà présente — skip.")

        if "justificatif_nom" not in cols:
            if dialect == "postgresql":
                migrations.append(
                    "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS justificatif_nom VARCHAR(255)"
                )
            else:
                migrations.append(
                    "ALTER TABLE resultats_theorie ADD COLUMN justificatif_nom VARCHAR(255)"
                )
        else:
            print("✅ justificatif_nom déjà présente — skip.")

        for sql in migrations:
            print(f"Exécution : {sql}")
            db.execute(text(sql))

        db.commit()
        if migrations:
            print("✅ Migration justificatif_theorie terminée.")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
