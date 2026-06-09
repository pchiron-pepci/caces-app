"""Migration : ajout colonne photo_base64 sur la table stagiaires."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non définie")

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE stagiaires ADD COLUMN IF NOT EXISTS photo_base64 TEXT"))
    conn.commit()
    print("OK — colonne photo_base64 ajoutée (ou déjà présente)")
