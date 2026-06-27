"""Peuple la grille d'evaluation pratique R.482 categorie F (base).
Source : fiche INRS A3/2/10, calee sur la feuille Excel OTC 'Pratique F'.
Idempotent : supprime puis recree la grille F base.
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
Base.metadata.create_all(bind=engine)

# Structure : themes -> [ (libelle_theme, bareme_theme, [ PE ]) ]
# PE : (numero, libelle_chapeau_ou_None, [ lignes ])
# ligne : (libelle, bareme)  -- bareme=None => descriptive (non notee)

THEMES = [
    ("Prise de poste et mise en service", 16, [
        ("1", None, [
            ("Verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :", 1),
            ("Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", None),
            ("Rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", 1),
            ("Proceder a une verification visuelle de l'engin de chantier", 1),
            ("Identifier les niveaux et les appoints journaliers", 1),
            ("Acceder au poste de conduite en securite (regle des 3 points d'appui)", 2),
            ("Effectuer les operations necessaires (reglages, nettoyage...) pour assurer la visibilite depuis le poste de conduite", 2),
            ("Effectuer le reglage du siege (position et suspension)", 2),
            ("Demarrer l'engin en respectant le mode operatoire prescrit", 2),
            ("Verifier le bon fonctionnement des organes de service et des differents indicateurs du tableau de bord", 1),
            ("Verifier le bon fonctionnement des dispositifs de securite", 2),
            ("Identifier la position de l'issue de secours et savoir expliquer sa mise en oeuvre", 1),
        ]),
    ]),
    ("Adequation", 12, [
        ("2", None, [
            ("Prendre connaissance des abaques de charge et savoir determiner la capacite du chariot en fonction de la hauteur et de la portee, dans les differentes configurations (sur pneumatiques, sur stabilisateurs...)", 4),
            ("S'assurer de l'adequation du chariot a la manutention a realiser (capacite, hauteur, portee...)", 4),
            ("Verifier que la configuration de la charge (support, nature, homogeneite, stabilite...) est compatible avec le levage", 4),
        ]),
    ]),
    ("Conduite et circulation", 30, [
        ("3", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage", 8),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", 3),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", 3),
            ("Respecter les conditions de stabilite de l'engin", 8),
            ("Maitriser la selection des vitesses", 2),
            ("Utiliser correctement les dispositifs de freinage", 2),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", 2),
            ("Respecter les regles et panneaux de circulation", 2),
        ]),
    ]),
    ("Travaux de base", 30, [
        ("4", None, [("Charger et decharger un camion en utilisant au moins trois charges", 15)]),
        ("5", None, [("Manutentionner une charge longue", 5)]),
        ("6", None, [("Manutentionner une charge lourde (minimum 50 % de la capacite du chariot)", 5)]),
        ("7", None, [("Manutentionner une charge complexe", 5)]),
    ]),
    ("Fin de poste - maintenance", 12, [
        ("8", None, [
            ("Stationner l'engin en securite", 2),
            ("Positionner les equipements de facon appropriee", 2),
            ("Mettre en oeuvre les securites", 2),
            ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", 2),
            ("Quitter le poste de conduite en securite (regle des 3 points d'appui)", 2),
            ("Mettre l'engin a l'arret", 2),
        ]),
    ]),
]

ELIMINATOIRES = [
    "Sauter de l'engin",
    "Ne pas garantir la securite des pietons",
    "Circuler avec une charge en hauteur",
    "Realiser une operation de levage avec un engin non equipe des dispositifs de securite appropries",
    "Quitter l'engin sans arreter le moteur",
]

db = SessionLocal()

# Suppression idempotente de la grille F base existante
anciennes = db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.482",
    GrillePratique.categorie == "F",
    GrillePratique.type == "base",
).all()
for g in anciennes:
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.482", categorie="F", type="base", code_option=None,
    libelle="Chariots de manutention tout-terrain",
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

# Recap de verification
print("[OK] Grille R.482 F base creee (id=%s)" % grille.id)
print("[OK] Total points notes : %s (attendu 100)" % total_grille)
for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
    somme = 0
    nb_pe = 0
    for pe in th.points:
        nb_pe += 1
        for it in pe.items:
            if it.bareme_max:
                somme += it.bareme_max
    print("   Theme '%s' : %s pts (bareme declare %s), %s PE, seuil %s" % (
        th.libelle, somme, th.bareme_theme, nb_pe, th.bareme_theme / 2))
print("[OK] %s criteres eliminatoires" % len(ELIMINATOIRES))
db.close()
