"""Migration : ajout token_verification sur carte_caces + backfill UUID pour cartes existantes."""
import os
import uuid
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE carte_caces ADD COLUMN IF NOT EXISTS token_verification VARCHAR(36) UNIQUE"
    ))
    conn.commit()

    # Backfill : generer un UUID pour chaque carte existante sans token
    rows = conn.execute(text("SELECT id FROM carte_caces WHERE token_verification IS NULL")).fetchall()
    for (row_id,) in rows:
        conn.execute(
            text("UPDATE carte_caces SET token_verification = :tok WHERE id = :id"),
            {"tok": str(uuid.uuid4()), "id": row_id}
        )
    conn.commit()
    print(f"OK — colonne token_verification ajoutee, {len(rows)} carte(s) backfillees")
