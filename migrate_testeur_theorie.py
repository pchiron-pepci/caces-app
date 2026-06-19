"""
Migration : ajoute testeur_id sur resultats_theorie.

Idempotent (IF NOT EXISTS) — sans risque sur une base déjà migrée.
Exécuter une seule fois via Render Shell :
    python migrate_testeur_theorie.py
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///caces.db")
engine = create_engine(DATABASE_URL)

SQL = "ALTER TABLE resultats_theorie ADD COLUMN IF NOT EXISTS testeur_id INTEGER REFERENCES testeurs(id)"

with engine.connect() as conn:
    conn.execute(text(SQL))
    conn.commit()
    print("OK : testeur_id ajouté à resultats_theorie (ou déjà présent).")
