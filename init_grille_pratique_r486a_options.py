"""Peuple la grille d'evaluation pratique de l'OPTION Porte-engins (PE) de R.486 A.
0,5 UT, note_max 50, seuil 35. Source Excel OTC. Idempotent."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.grille_pratique import (
    GrillePratique, ThemePratique, PointEvaluation, ItemPratique
)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine, tables=[
    GrillePratique.__table__, ThemePratique.__table__,
    PointEvaluation.__table__, ItemPratique.__table__,
])

THEMES = [
    ("Chargement de la PEMP (3A)", 15, [
        ("1", None, [
            ("S'assurer de l'adéquation de le PEMP et du porte-engins à la manœuvre prévue", 3),
            ("S'assurer que la position du véhicule est appropriée", 3),
            ("Vérifier que les conditions permettant le chargement / déchargement sont remplies (espacement des rampes)", 3),
            ("Monter la PEMP sur le porte-engins dans le sens approprié", 6),
        ]),
    ]),
    ("Préparation au transport", 10, [
        ("2", None, [
            ("Positionner la PEMP sur le porte-engins pour assurer l'équilibre et la stabilité", 4),
            ("Mettre la PEMP en configuration de transport", 3),
            ("Stabiliser la PEMP (freins, stabilisateurs, cales…)", 3),
        ]),
    ]),
    ("Préparation à l'arrimage", 10, [
        ("3", None, [
            ("Identifier et désigner les points d'arrimage sur le porte-engins", 2),
            ("Identifier et désigner les points d'arrimage sur la PEMP", 2),
            ("Trouver le mode d'arrimage approprié (notice d'instructions…)", 3),
            ("S'assurer de l'adéquation des moyens d'arrimage proposés", 3),
        ]),
    ]),
    ("Décharg. de la PEMP (3A)", 15, [
        ("4", None, [
            ("S'assurer que l'environnement du porte-engins permet le déchargement", 3),
            ("Positionner la PEMP pour la descente", 5),
            ("Descendre la PEMP en sécurité", 7),
        ]),
    ]),
]

db = SessionLocal()
for g in db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.486",
    GrillePratique.categorie == "A",
    GrillePratique.type == "option",
    GrillePratique.code_option == "PE",
).all():
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.486", categorie="A", type="option", code_option="PE",
    libelle="Porte-engins", ut=0.5, note_min=35, note_max=50, version="2025", ordre=0, actif=True,
)
db.add(grille)
db.flush()
total = 0
for ordre_th, (lib_th, bareme_th, pes) in enumerate(THEMES):
    theme = ThemePratique(grille_id=grille.id, libelle=lib_th, bareme_theme=bareme_th, ordre=ordre_th)
    db.add(theme); db.flush()
    for ordre_pe, (num, chapeau, lignes) in enumerate(pes):
        pe = PointEvaluation(theme_id=theme.id, numero=num, libelle_chapeau=chapeau, ordre=ordre_pe)
        db.add(pe); db.flush()
        for ordre_l, (lib, bareme) in enumerate(lignes):
            db.add(ItemPratique(pe_id=pe.id, libelle=lib, bareme_max=bareme,
                descriptif_seul=(bareme is None), ordre=ordre_l))
            if bareme: total += bareme
db.commit()
print("[OK] Grille R.486 A option PE creee (id=%s), total %s (attendu 50)" % (grille.id, total))
