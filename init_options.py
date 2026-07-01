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
    ("R482", "C3",     [("PE", False), ("TEL", False)]),    # nivellement : PE + TEL facultatives (TEL au referentiel)
    ("R482", "D",      [("PE", False), ("TEL", False)]),
    ("R482", "E",      [("PE", False), ("TEL", False)]),    # tombereau : PE + TEL facultatives (TEL prevue au referentiel)
    ("R482", "F",      [("PE", False), ("TEL", False)]),    # tout-terrain, PE+TEL facultatives
    ("R482", "G",      [("TEL", False)]),                   # G = porte-engins par nature (pas de PE), TEL facultative
    ("R482", "H",      [("TEL", False)]),
    ("R483", "A",      [("CC", True),  ("CEC", True),  ("TEL", False)]),  # CC+CEC incluses, TEL facultative
    ("R483", "B",      [("CC", True),  ("CEC", False), ("TEL", False)]),  # CC incluse, CEC+TEL facultatives
    ("R486", "A",      [("PE", False)]),
    ("R486", "B",      [("PE", False)]),
    ("R486", "C",      [("PE", True)]),                    # PE incluse dans l'UT
    ("R487", "1",      [("CEC", True),  ("TEL", False), ("TR", False)]),  # CEC incluse, grues a tour type 1
    ("R487", "2",      [("CEC", True),  ("TEL", False), ("TR", False)]),  # CEC incluse, grues a tour type 2
    ("R487", "3",      [("TEL", True),  ("CEC", False), ("TR", False)]),  # TEL incluse, fleche relevable
    ("R490", "1",      [("TEL", False)]),
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
