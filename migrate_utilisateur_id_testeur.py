"""Migration : ajout colonne utilisateur_id (FK utilisateurs) sur testeurs."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
is_sqlite = DATABASE_URL.startswith("sqlite")

with engine.connect() as conn:
    if is_sqlite:
        # SQLite : pas de ADD COLUMN IF NOT EXISTS avant SQLite 3.37 — on vérifie d'abord
        cols = conn.execute(text("PRAGMA table_info(testeurs)")).fetchall()
        col_names = [c[1] for c in cols]
        if "utilisateur_id" not in col_names:
            conn.execute(text("ALTER TABLE testeurs ADD COLUMN utilisateur_id INTEGER REFERENCES utilisateurs(id)"))
            conn.commit()
            print("OK — utilisateur_id ajouté à testeurs (SQLite)")
        else:
            print("Colonne utilisateur_id déjà présente, ignorée.")
    else:
        # PostgreSQL
        conn.execute(text(
            "ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS utilisateur_id INTEGER UNIQUE REFERENCES utilisateurs(id)"
        ))
        conn.commit()
        print("OK — utilisateur_id ajouté à testeurs (PostgreSQL)")
