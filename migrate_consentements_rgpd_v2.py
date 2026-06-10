import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE consentements_rgpd ADD COLUMN IF NOT EXISTS verificateur_identite VARCHAR(200)"
    ))
    conn.execute(text(
        "ALTER TABLE consentements_rgpd ADD COLUMN IF NOT EXISTS horodatage_verification TIMESTAMP"
    ))
    conn.commit()

print("OK : colonnes verificateur_identite et horodatage_verification ajoutees")
