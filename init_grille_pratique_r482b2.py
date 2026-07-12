"""Peuple la grille d'evaluation pratique R.482 categorie B2 (base), MULTI-VARIANTE EXCLUSIVE.
B2 = engins de forage a deplacement sequentiel. Le candidat passe UNE variante :
- CA = conducteur accompagnant (TELECOMMANDE INTEGREE dans la grille, pas de module TEL separe, comme le PE du A)
- CP = conducteur porte (poste de conduite classique)
Les deux grilles sont ASYMETRIQUES (items ET baremes differents, notamment en Prise de poste).
Chaque variante = 100 pts : Prise/16 + Conduite/32 + Travaux/40 + Fin/12.
Option PE (porte-engins) facultative commune (script separe). Pas d'option TEL (integree dans CA).
Source : referentiel INRS R.482 (grille officielle B2, feuilles Excel 'Pratique B2 - CA' et '- CP').
Idempotent. B2 base = 1,0 UT.
"""
import os
from sqlalchemy import create_engine, text
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
    PointEvaluation.__table__, ItemPratique.__table__, CritereEliminatoire.__table__,
])

with engine.begin() as cx:
    try:
        cx.execute(text("ALTER TABLE grille_pratique ADD COLUMN variante VARCHAR(10)"))
        print("[OK] colonne 'variante' ajoutee")
    except Exception:
        print("[INFO] colonne 'variante' deja presente")

# ---- Variante CA : conducteur accompagnant (telecommande integree) ----
THEMES_CA = [
    ("Prise de poste et mise en service", 16, [
        ("1", "Verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :", [
            ("Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", 1),
            ("Rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", 1),
            ("Proceder a une verification visuelle de l'engin de chantier", 1),
            ("Identifier les niveaux et les appoints journaliers", 1),
            ("Demarrer l'engin en respectant le mode operatoire prescrit", 2),
            ("Verifier le bon fonctionnement de la telecommande (equipements de transmission, boutons, voyants...), notamment l'arret d'urgence et la cle de condamnation", 2),
            ("Verifier l'impossibilite de fonctionnement simultane de la telecommande et du poste de conduite principal", 2),
            ("Enumerer les risques lies a l'utilisation de la telecommande", 2),
            ("Savoir se positionner par rapport a la zone de travail", 2),
            ("Verifier le bon fonctionnement des dispositifs de securite", 2),
        ]),
    ]),
    ("Conduite et circulation", 32, [
        ("2", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage, selon le parcours de test defini (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage, selon le parcours de test defini", 8),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", 4),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", 4),
            ("Respecter les conditions de stabilite de l'engin", 4),
            ("Maitriser la selection des vitesses", 4),
            ("Utiliser correctement les dispositifs de freinage", 4),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", 4),
        ]),
    ]),
    ("Travaux de base", 40, [
        ("3", "Realiser un forage", [
            ("Configurer la machine en mode forage", 2),
            ("Positionner la machine par rapport au point de forage", 3),
            ("Stabiliser la machine en fonction de la nature du sol", 3),
            ("S'assurer de l'orientation correcte du mat de forage", 3),
            ("Positionner le poste de commande afin de disposer d'une bonne visibilite sur la zone de travail", 3),
            ("Amenager la plate-forme de travail pour permettre l'evacuation des sediments", 3),
            ("Approvisionner et organiser l'unite de travail (fluides, outillages, consommables...)", 3),
            ("Proceder au forage", 10),
            ("Realiser le retrait des tiges de forage", 5),
            ("Assurer le demontage des raccords, tubes, tiges, outils...", 3),
            ("Proceder a la configuration de la machine en mode deplacement", 2),
        ]),
    ]),
    ("Operation de fin de poste - maintenance", 12, [
        ("4", None, [
            ("Stationner l'engin en securite", 2),
            ("Positionner les equipements de facon appropriee", 2),
            ("Mettre en oeuvre les securites", 2),
            ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", 2),
            ("Mettre la telecommande a l'arret et la ranger", 2),
            ("Mettre l'engin a l'arret", 2),
        ]),
    ]),
]

# ---- Variante CP : conducteur porte (poste de conduite classique) ----
THEMES_CP = [
    ("Prise de poste et mise en service", 16, [
        ("1", "Verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :", [
            ("Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", 1),
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
    ("Conduite et circulation", 32, [
        ("2", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage, selon le parcours de test defini (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage, selon le parcours de test defini", 8),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", 4),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", 4),
            ("Respecter les conditions de stabilite de l'engin", 4),
            ("Maitriser la selection des vitesses", 4),
            ("Utiliser correctement les dispositifs de freinage", 4),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", 4),
        ]),
    ]),
    ("Travaux de base", 40, [
        ("3", "Realiser un forage", [
            ("Configurer la machine en mode forage", 2),
            ("Positionner la machine par rapport au point de forage", 3),
            ("Stabiliser la machine en fonction de la nature du sol", 3),
            ("S'assurer de l'orientation correcte du mat de forage", 3),
            ("Positionner le poste de commande afin de disposer d'une bonne visibilite sur la zone de travail", 3),
            ("Amenager la plate-forme de travail pour permettre l'evacuation des sediments", 3),
            ("Approvisionner et organiser l'unite de travail (fluides, outillages, consommables...)", 3),
            ("Proceder au forage", 10),
            ("Realiser le retrait des tiges de forage", 5),
            ("Assurer le demontage des raccords, tubes, tiges, outils...", 3),
            ("Proceder a la configuration de la machine en mode deplacement", 2),
        ]),
    ]),
    ("Operation de fin de poste - maintenance", 12, [
        ("4", None, [
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

VARIANTES = [
    ("CA", "Engins de forage - conducteur accompagnant (telecommande)", THEMES_CA, 0),
    ("CP", "Engins de forage - conducteur porte", THEMES_CP, 1),
]

db = SessionLocal()

for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "B2",
        GrillePratique.type == "base").all():
    db.delete(g)
db.commit()

for variante, libelle, themes, ordre in VARIANTES:
    grille = GrillePratique(
        recommandation="R.482", categorie="B2", type="base", code_option=None,
        variante=variante, libelle=libelle,
        ut=1.0, note_min=70, note_max=100, version="2025", ordre=ordre, actif=True,
    )
    db.add(grille)
    db.flush()

    total = 0
    for ordre_th, (lib_th, bareme_th, pes) in enumerate(themes):
        theme = ThemePratique(grille_id=grille.id, libelle=lib_th, bareme_theme=bareme_th, ordre=ordre_th)
        db.add(theme)
        db.flush()
        for ordre_pe, (num, chapeau, lignes) in enumerate(pes):
            pe = PointEvaluation(theme_id=theme.id, numero=num, libelle_chapeau=chapeau, ordre=ordre_pe)
            db.add(pe)
            db.flush()
            for ordre_l, (lib, bareme) in enumerate(lignes):
                db.add(ItemPratique(
                    pe_id=pe.id, libelle=lib, bareme_max=bareme,
                    descriptif_seul=(bareme is None), ordre=ordre_l,
                ))
                if bareme:
                    total += bareme

    for ordre_e, lib_e in enumerate(ELIMINATOIRES):
        db.add(CritereEliminatoire(grille_id=grille.id, libelle=lib_e, ordre=ordre_e))
    db.commit()

    print("[OK] Grille B2 %s creee (id=%s) - total %s (attendu 100)" % (variante, grille.id, total))
    for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
        s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
        flag = "OK" if s == th.bareme_theme else "!!! ECART"
        print("   Theme '%s' : %s pts (declare %s, seuil %s) [%s]" % (th.libelle, s, th.bareme_theme, th.bareme_theme / 2, flag))

db.close()
print("[OK] 2 grilles B2 (CA/CP) exclusives en base.")