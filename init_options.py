"""Peuple la table option_categorie avec les options CACES® disponibles par famille/catégorie."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.option_categorie import OptionCategorie
from app.database import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

LIBELLES = {
    "PE": "Porte-engins",
    "TEL": "Télécommande",
    "CC": "Conduite cabine",
    "TR": "Translation sur rails",
    "CEC": "Circulation en charge",
}

OPTIONS = [
    ("R482", "A",      ["PE", "TEL"]),
    ("R482", "B1",     ["PE", "TEL"]),
    ("R482", "C1",     ["PE"]),
    ("R482", "C2",     ["PE"]),
    ("R482", "C3",     ["PE"]),
    ("R482", "D",      ["PE", "TEL"]),
    ("R482", "E",      ["PE"]),
    ("R482", "H",      ["TEL"]),
    ("R483", "A",      ["TEL", "CEC"]),
    ("R483", "B",      ["TEL", "CEC"]),
    ("R486", "A",      ["PE"]),
    ("R486", "B",      ["PE"]),
    ("R487", "1",      ["TEL", "CC", "TR"]),
    ("R487", "2",      ["TEL", "CC", "TR"]),
    ("R487", "3",      ["TEL", "CC", "TR"]),
    ("R490", "Unique", ["TEL"]),
]

db = SessionLocal()

# Vider et repeupler
db.query(OptionCategorie).delete()
for famille, categorie, codes in OPTIONS:
    for code in codes:
        db.add(OptionCategorie(
            famille=famille,
            categorie=categorie,
            code_option=code,
            libelle_option=LIBELLES[code]
        ))

db.commit()
db.close()
print(f"✅ {sum(len(c) for _, _, c in OPTIONS)} options insérées.")
