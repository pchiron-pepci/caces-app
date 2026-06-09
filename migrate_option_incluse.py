"""Migration : ajout colonne incluse sur la table option_categorie."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE option_categorie ADD COLUMN IF NOT EXISTS incluse BOOLEAN DEFAULT FALSE"))
    conn.commit()
    print("OK — colonne incluse ajoutee (ou deja presente)")
