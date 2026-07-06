"""Peuple la grille d'evaluation pratique R.486 categorie C (base).
Source : fiche INRS + feuille Excel OTC 'Pratique C'. Idempotent.
Cat C : conduite hors production, porte-engins INTEGRE dans la base (pas d'option PE separee).
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
    ("Prise de poste et mise en service (1A, 1B ou 3B)", 10, [
        ("1", None, [
            ("Notice d'instructions (justifier une interdiction d'emploi ou une règle d'utilisation)", 1),
            ("Rapport de vérification générale périodique, de mise ou de remise en service (vérifier l'absence d'observation ou de restriction d'usage)", 2),
        ]),
        ("2", None, [
            ("Procéder à une vérification visuelle de la PEMP", 3),
            ("Vérifier le bon fonctionnement des mécanismes et des dispositifs de sécurité accessibles", 4),
        ]),
    ]),
    ("Adé.", 10, [
        ("3", None, [
            ("Identifier les risques liés à la zone d'évolution", 10),
        ]),
    ]),
    ("Mise en place (1A ou 1B)", 17, [
        ("4", None, [
            ("Baliser la zone d'intervention", 5),
            ("Déployer les stabilisateurs", 3),
            ("Régler l'horizontalité de la PEMP", 6),
            ("Replier les stabilisateurs", 3),
        ]),
    ]),
    ("Conduite et manœuvres (3B)", 36, [
        ("5", None, [
            ("Adapter sa conduite aux conditions de circulation (évalué en continu)", 2),
            ("Effectuer les manoeuvres avec souplesse et précision (évalué en continu)", 2),
            ("Regarder en arrière avant de reculer (évalué en continu)", 2),
            ("Utiliser correctement l'avertisseur sonore (évalué en continu)", 2),
            ("Respecter les règles et panneaux de circulation (évalué en continu)", 2),
            ("Comprendre / exécuter les gestes de commandement (évalué en continu)", 2),
            ("Savoir réagir à un signal d'alerte (évalué en continu)", 2),
        ]),
        ("6", None, [
            ("Positionner la PEMP à un emplacement précis (aire limitée au sol)", 4),
            ("Circuler plate-forme en position basse orientée dans le sens de la marche, en marche avant / arrière, en ligne droite / en virages", 6),
            ("Circuler plate-forme en position basse orientée dans le sens inverse de la marche, en marche avant / arrière, en ligne droite / en virages", 6),
            ("Effectuer les manoeuvres de secours (au moyen des commandes de secours et de dépannage)", 6),
        ]),
    ]),
    ("Chargement / déchargement sur un porte-engins (3B)", 22, [
        ("7", None, [
            ("S'assurer de l'adéquation de la PEMP et du porte-engins", 2),
            ("Vérifier que les conditions permettant le chargement / déchargement sont remplies", 2),
            ("Monter la PEMP sur le porte-engins dans le sens approprié", 2),
        ]),
        ("8", None, [
            ("Positionner la PEMP sur le porte-engins pour assurer l'équilibre et la stabilité", 2),
            ("Mettre la PEMP en configuration de transport et la stabiliser", 3),
        ]),
        ("9", None, [
            ("Identifier et désigner les points d'arrimage sur le porte-engins et sur la PEMP", 2),
            ("Trouver le mode d'arrimage approprié (notice d'instructions…)", 2),
            ("S'assurer de l'adéquation des moyens d'arrimage proposés", 2),
        ]),
        ("10", None, [
            ("S'assurer que l'environnement du porte-engins permet le déchargement", 2),
            ("Positionner la PEMP pour la descente et la descendre en sécurité", 3),
        ]),
    ]),
    ("Fin de poste (1A, 1B ou 3B)", 5, [
        ("11", None, [
            ("Mettre la PEMP en position hors-service", 2),
            ("Réaliser des opérations de maintenance journalière", 2),
            ("Rendre compte des anomalies relevées", 1),
        ]),
    ]),
]

ELIMINATOIRES = []  # R.486 : pas de liste transversale (referentiel INRS)

db = SessionLocal()
anciennes = db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.486",
    GrillePratique.categorie == "C",
    GrillePratique.type == "base",
).all()
for g in anciennes:
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.486", categorie="C", type="base", code_option=None,
    libelle="Conduite hors production des PEMP (types 1 et 3)",
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
print("[OK] Grille R.486 C base creee (id=%s)" % grille.id)
print("[OK] Total points notes : %s (attendu 100)" % total_grille)
for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
    somme = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
    print("   Theme %s : %s pts (declare %s), seuil %s" % (th.libelle, somme, th.bareme_theme, th.bareme_theme/2))
print("[OK] %s criteres eliminatoires" % len(ELIMINATOIRES))
