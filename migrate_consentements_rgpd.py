import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS consentements_rgpd (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL,
            stagiaire_id INTEGER NOT NULL,
            rgpd_accepte BOOLEAN,
            photo_accepte BOOLEAN,
            plaintes_atteste BOOLEAN,
            signature_base64 TEXT,
            horodatage TIMESTAMP,
            ip_address VARCHAR(50),
            CONSTRAINT uq_consentement_session_stagiaire UNIQUE(session_id, stagiaire_id)
        )
    """))
    conn.commit()

print("OK : table consentements_rgpd creee (ou deja existante)")
