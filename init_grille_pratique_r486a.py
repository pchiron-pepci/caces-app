"""Peuple la grille d'evaluation pratique R.486 categorie A (base).
Source : fiche INRS + feuille Excel OTC 'Pratique A'. Idempotent.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.grille_pratique import (
    GrillePratique, ThemePratique, PointEvaluation, ItemPratique, CritereEliminatoire
)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine, tables=[
    GrillePratique.__table__, ThemePratique.__table__,
    PointEvaluation.__table__, ItemPratique.__table__,
    CritereEliminatoire.__table__,
])

# themes -> (libelle, bareme, [PE]) ; PE -> (numero, chapeau|None, [(libelle,bareme|None)])
THEMES = [
    ("Prise de poste et mise en service (1A ou 3A)", 15, [
        ("1", None, [
            ("Notice d'instructions (justifier une interdiction d'emploi ou une règle d'utilisation)", 2),
            ("Rapport de vérification générale périodique, de mise ou de remise en service (vérifier l'absence d'observation ou de restriction d'usage)", 2),
        ]),
        ("2", None, [
            ("Procéder à une vérification visuelle de la PEMP", 4),
            ("Vérifier le bon fonctionnement des mécanismes et des dispositifs de sécurité accessibles", 5),
            ("Evaluer les conditions météorologiques", 2),
        ]),
    ]),
    ("Adé. (1A ou 3A)", 6, [
        ("3", None, [
            ("Vérifier l'adéquation de la PEMP aux opérations à effectuer", 3),
            ("Identifier les risques liés à la zone d'évolution", 3),
        ]),
    ]),
    ("Mise en place, conduite et manœuvres (1A)", 35, [
        ("4", None, [
            ("Baliser la zone d'intervention", 2),
            ("Déployer les stabilisateurs", 3),
            ("Régler l'horizontalité de la PEMP", 3),
            ("Replier les stabilisateurs", 3),
        ]),
        ("5", None, [
            ("Effectuer les manœuvres avec souplesse et précision (évalué en continu)", 3),
            ("Comprendre / Exécuter les gestes de commandement (évalué en continu)", 3),
            ("Savoir réagir à un signal d'alerte (évalué en continu)", 3),
        ]),
        ("6", None, [
            ("Positionner la PEMP à un emplacement précis (aire limitée au sol)", 3),
            ("Positionner la PEMP le long d'une paroi plane verticale", 3),
            ("Déplacer la plate-forme le long d'une paroi plane verticale", 3),
            ("Positionner la plate-forme sous une paroi plane horizontale", 3),
            ("Effectuer les manoeuvres de secours (au moyen des commandes de secours et de dépannage)", 3),
        ]),
    ]),
    ("Manœuvres et conduite (3A)", 34, [
        ("7", None, [
            ("Adapter sa conduite aux conditions de circulation (évalué en continu)", 2),
            ("Effectuer les manœuvres avec souplesse et précision (évalué en continu)", 2),
            ("Regarder en arrière avant de reculer (évalué en continu)", 3),
            ("Utiliser correctement l'avertisseur sonore (évalué en continu)", 1),
            ("Respecter les règles et panneaux de circulation (évalué en continu)", 1),
            ("Comprendre / exécuter les gestes de commandement (évalué en continu)", 1),
            ("Savoir réagir à un signal d'alerte (évalué en continu)", 1),
        ]),
        ("8", None, [
            ("Positionner la PEMP à un emplacement précis (aire limitée au sol)", 2),
            ("Circuler plate-forme en position haute (4 m mini), dans le sens de la marche, en marche avant / arrière, en ligne droite / en virages", 4),
            ("Circuler plate-forme en position haute (4 m mini), dans le sens inverse de la marche, en marche avant / arrière, en ligne droite / en virages", 4),
            ("Positionner la PEMP le long d'une paroi plane verticale", 2),
            ("Déplacer la plate-forme le long d'une paroi plane verticale", 2),
            ("Positionner la PEMP sous une paroi plane horizontale", 2),
            ("Déplacer la plate-forme sous une paroi plane horizontale", 2),
            ("Positionner la plate-forme à un emplacement précis en élévation", 2),
            ("Effectuer des manœuvres de secours (au moyen des commandes de secours et de dépannage)", 3),
        ]),
    ]),
    ("Fin de poste (1A ou 3A)", 10, [
        ("9", None, [
            ("Mettre la PEMP en position hors-service", 5),
            ("Réaliser des opérations de maintenance journalière", 3),
            ("Rendre compte des anomalies relevées", 2),
        ]),
    ]),
]

ELIMINATOIRES = []  # R.486 : pas de liste transversale (referentiel INRS)

db = SessionLocal()
anciennes = db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.486",
    GrillePratique.categorie == "A",
    GrillePratique.type == "base",
).all()
for g in anciennes:
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.486", categorie="A", type="base", code_option=None,
    libelle="PEMP a elevation verticale (types 1 et 3)",
    ut=1.0, note_min=70, note_max=100, version="2025", ordre=0, actif=True,
)
db.add(grille)
db.flush()

total_grille = 0
for ordre_th, (lib_th, bareme_th, pes) in enumerate(THEMES):
    theme = ThemePratique(grille_id=grille.id, libelle=lib_th, bareme_theme=bareme_th, ordre=ordre_th)
    db.add(theme)
    db.flush()
    for ordre_pe, (num, chapeau, lignes) in enumerate(pes):
        pe = PointEvaluation(theme_id=theme.id, numero=num, libelle_chapeau=chapeau, ordre=ordre_pe)
        db.add(pe)
        db.flush()
        for ordre_l, (lib, bareme) in enumerate(lignes):
            item = ItemPratique(
                pe_id=pe.id, libelle=lib, bareme_max=bareme,
                descriptif_seul=(bareme is None), ordre=ordre_l,
            )
            db.add(item)
            if bareme:
                total_grille += bareme

for ordre_e, lib_e in enumerate(ELIMINATOIRES):
    db.add(CritereEliminatoire(grille_id=grille.id, libelle=lib_e, ordre=ordre_e))

db.commit()
print("[OK] Grille R.486 A base creee (id=%s)" % grille.id)
print("[OK] Total points notes : %s (attendu 100)" % total_grille)
for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
    somme = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
    print("   Theme %s : %s pts (declare %s), seuil %s" % (th.libelle, somme, th.bareme_theme, th.bareme_theme/2))
print("[OK] %s criteres eliminatoires" % len(ELIMINATOIRES))
