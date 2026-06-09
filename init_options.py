"""Peuple la table option_categorie avec les options CACES(r) disponibles par famille/categorie."""
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
    "PE":  "Porte-engins",
    "TEL": "Telecommande",
    "CC":  "Conduite cabine",
    "TR":  "Translation sur rails",
    "CEC": "Circulation en charge",
}

# (famille, categorie, [(code_option, incluse)])
# incluse=True : option obligatoire incluse dans l'UT de la categorie (pas de +0.5 UT)
# incluse=False : option facultative, ajoute +0.5 UT
OPTIONS = [
    ("R482", "A",      [("PE", True),  ("TEL", False)]),
    ("R482", "B1",     [("PE", False), ("TEL", False)]),
    ("R482", "B2",     [("TEL", True)]),                   # conducteur accompagnant
    ("R482", "C1",     [("PE", False)]),
    ("R482", "C2",     [("PE", False)]),
    ("R482", "C3",     [("PE", False)]),
    ("R482", "D",      [("PE", False), ("TEL", False)]),
    ("R482", "E",      [("PE", False)]),
    ("R482", "G",      [("TEL", True), ("PE", False)]),     # telescopique, TEL incluse, PE facultative
    ("R482", "H",      [("TEL", False)]),
    ("R483", "A",      [("TEL", False), ("CEC", False)]),
    ("R483", "B",      [("TEL", False), ("CEC", False)]),
    ("R486", "A",      [("PE", False)]),
    ("R486", "B",      [("PE", False)]),
    ("R487", "1",      [("TEL", False), ("CC", False), ("TR", False)]),
    ("R487", "2",      [("TEL", False), ("CC", False), ("TR", False)]),
    ("R487", "3",      [("TEL", False), ("CC", False), ("TR", False)]),
    ("R490", "Unique", [("TEL", False)]),
]

db = SessionLocal()

db.query(OptionCategorie).delete()
count = 0
for famille, categorie, opts in OPTIONS:
    for code, incluse in opts:
        db.add(OptionCategorie(
            famille=famille,
            categorie=categorie,
            code_option=code,
            libelle_option=LIBELLES[code],
            incluse=incluse,
        ))
        count += 1

db.commit()
db.close()
print(f"{count} options inserees.")
