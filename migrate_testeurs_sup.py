"""Migration : ajout colonne testeurs_sup TEXT sur jours_test."""
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE jours_test ADD COLUMN IF NOT EXISTS testeurs_sup TEXT"
    ))
    conn.commit()
    print("OK — testeurs_sup ajouté à jours_test")
