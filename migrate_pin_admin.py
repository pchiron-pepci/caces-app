"""Ajoute pin_admin à config_organisme et initialise à '1505'."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # PostgreSQL : ADD COLUMN IF NOT EXISTS
    # SQLite ne supporte pas IF NOT EXISTS sur ADD COLUMN — on attrape l'erreur
    try:
        conn.execute(text("ALTER TABLE config_organisme ADD COLUMN pin_admin VARCHAR(20)"))
        conn.commit()
        print("Colonne pin_admin ajoutée.")
    except Exception as e:
        print(f"Colonne déjà présente ou erreur : {e}")
        conn.rollback()

    # Initialiser à '1505' là où NULL
    with engine.connect() as conn2:
        conn2.execute(text("UPDATE config_organisme SET pin_admin = '1505' WHERE pin_admin IS NULL"))
        conn2.commit()
        print("pin_admin initialisé à '1505' pour les lignes existantes.")
