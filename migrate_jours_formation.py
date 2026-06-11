"""Migration : création des tables jours_formation, affectations_formation,
planning_apprenants, affectations_test.

Migration additive pure — aucune table existante modifiée.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)

TABLES = [
    (
        "jours_formation",
        """
        CREATE TABLE jours_formation (
            id                    SERIAL PRIMARY KEY,
            session_id            INTEGER NOT NULL REFERENCES sessions(id),
            date                  DATE NOT NULL,
            intitule              VARCHAR(200),
            libelle_colonne_libre VARCHAR(100),
            note                  TEXT,
            actif                 BOOLEAN DEFAULT TRUE
        )
        """,
    ),
    (
        "affectations_formation",
        """
        CREATE TABLE affectations_formation (
            id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            jour_formation_id INTEGER NOT NULL REFERENCES jours_formation(id),
            user_id           INTEGER NOT NULL REFERENCES utilisateurs(id),
            theorie           BOOLEAN DEFAULT FALSE,
            pratique          BOOLEAN DEFAULT FALSE,
            principal         BOOLEAN DEFAULT FALSE,
            UNIQUE (jour_formation_id, user_id)
        )
        """,
    ),
    (
        "planning_apprenants",
        """
        CREATE TABLE planning_apprenants (
            id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            jour_formation_id INTEGER NOT NULL REFERENCES jours_formation(id),
            stagiaire_id      INTEGER NOT NULL REFERENCES stagiaires(id),
            heures_theorie    FLOAT DEFAULT 0.0,
            heures_par_cat    TEXT,
            heures_libre      FLOAT DEFAULT 0.0,
            actif             BOOLEAN DEFAULT TRUE,
            UNIQUE (jour_formation_id, stagiaire_id)
        )
        """,
    ),
    (
        "affectations_test",
        """
        CREATE TABLE affectations_test (
            id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            jour_test_id INTEGER NOT NULL REFERENCES jours_test(id),
            user_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
            role         VARCHAR(20) DEFAULT 'testeur',
            principal    BOOLEAN DEFAULT FALSE,
            UNIQUE (jour_test_id, user_id)
        )
        """,
    ),
]

# SQLite ne supporte pas SERIAL ni GENERATED ALWAYS AS IDENTITY
TABLES_SQLITE = [
    (
        "jours_formation",
        """
        CREATE TABLE IF NOT EXISTS jours_formation (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id            INTEGER NOT NULL REFERENCES sessions(id),
            date                  DATE NOT NULL,
            intitule              VARCHAR(200),
            libelle_colonne_libre VARCHAR(100),
            note                  TEXT,
            actif                 BOOLEAN DEFAULT 1
        )
        """,
    ),
    (
        "affectations_formation",
        """
        CREATE TABLE IF NOT EXISTS affectations_formation (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            jour_formation_id INTEGER NOT NULL REFERENCES jours_formation(id),
            user_id           INTEGER NOT NULL REFERENCES utilisateurs(id),
            theorie           BOOLEAN DEFAULT 0,
            pratique          BOOLEAN DEFAULT 0,
            principal         BOOLEAN DEFAULT 0,
            UNIQUE (jour_formation_id, user_id)
        )
        """,
    ),
    (
        "planning_apprenants",
        """
        CREATE TABLE IF NOT EXISTS planning_apprenants (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            jour_formation_id INTEGER NOT NULL REFERENCES jours_formation(id),
            stagiaire_id      INTEGER NOT NULL REFERENCES stagiaires(id),
            heures_theorie    REAL DEFAULT 0.0,
            heures_par_cat    TEXT,
            heures_libre      REAL DEFAULT 0.0,
            actif             BOOLEAN DEFAULT 1,
            UNIQUE (jour_formation_id, stagiaire_id)
        )
        """,
    ),
    (
        "affectations_test",
        """
        CREATE TABLE IF NOT EXISTS affectations_test (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            jour_test_id INTEGER NOT NULL REFERENCES jours_test(id),
            user_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
            role         VARCHAR(20) DEFAULT 'testeur',
            principal    BOOLEAN DEFAULT 0,
            UNIQUE (jour_test_id, user_id)
        )
        """,
    ),
]

is_sqlite = DATABASE_URL.startswith("sqlite")
tables = TABLES_SQLITE if is_sqlite else TABLES

with engine.connect() as conn:
    for table_name, ddl in tables:
        try:
            if is_sqlite:
                conn.execute(text(ddl))
                conn.commit()
                print(f"Table {table_name} créée (SQLite).")
            else:
                # PostgreSQL : vérifie si la table existe déjà
                exists = conn.execute(
                    text("SELECT to_regclass(:name)"),
                    {"name": f"public.{table_name}"},
                ).scalar()
                if exists:
                    print(f"Table {table_name} déjà présente, ignorée.")
                else:
                    conn.execute(text(ddl))
                    conn.commit()
                    print(f"Table {table_name} créée.")
        except Exception as e:
            print(f"Erreur sur {table_name} : {e}")
            conn.rollback()

print("Migration jours_formation terminée.")
