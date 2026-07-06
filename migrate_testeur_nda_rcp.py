"""Migration idempotente : ajoute numero_nda + RCP (cle/nom/date) sur testeurs."""
from sqlalchemy import text
from app.database import engine

def run():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS numero_nda VARCHAR(50)"))
        conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS rcp_cle VARCHAR(500)"))
        conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS rcp_nom VARCHAR(200)"))
        conn.execute(text("ALTER TABLE testeurs ADD COLUMN IF NOT EXISTS rcp_date DATE"))
    print("OK : colonnes numero_nda + rcp_* pretes sur testeurs")

if __name__ == "__main__":
    run()
