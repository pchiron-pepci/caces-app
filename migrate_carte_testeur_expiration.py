"""Migration idempotente : ajoute carte_testeur.date_expiration (nullable)."""
from sqlalchemy import text
from app.database import engine

def run():
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE carte_testeur ADD COLUMN IF NOT EXISTS date_expiration DATE"
        ))
    print("OK : colonne date_expiration prete sur carte_testeur")

if __name__ == "__main__":
    run()
