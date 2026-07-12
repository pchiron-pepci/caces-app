"""Peuple la grille d'evaluation pratique R.482 categorie C2 (base), mono-grille.
C2 = engins de reglage a deplacement alternatif. 100 pts : Prise/16 + Conduite/42 + Travaux/30 + Fin/12.
Seuil par theme = bareme/2 (regle standard). Options PE et TEL facultatives (script separe).
Source : referentiel INRS R.482 A3/2, feuille Excel OTC 'Pratique C2'.
Idempotent. C2 base = 1,0 UT.
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
    PointEvaluation.__table__, ItemPratique.__table__, CritereEliminatoire.__table__,
])

THEMES = [
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
    ("Conduite et circulation", 42, [
        ("2", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage", 10),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", 5),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", 5),
            ("Respecter les conditions de stabilite de l'engin", 5),
            ("Maitriser la selection des vitesses", 5),
            ("Utiliser correctement les dispositifs de freinage", 5),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", 5),
            ("Respecter les regles et panneaux de circulation", 2),
        ]),
    ]),
    ("Travaux de base", 30, [
        ("3", None, [("Realiser le reglage d'une plate-forme", 15)]),
        ("4", None, [("Executer un deblai / remblai", 15)]),
    ]),
    ("Operation de fin de poste - maintenance", 12, [
        ("5", None, [
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

for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "C2",
        GrillePratique.type == "base").all():
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.482", categorie="C2", type="base", code_option=None,
    libelle="Engins de reglage a deplacement alternatif",
    ut=1.0, note_min=70, note_max=100, version="2025", ordre=0, actif=True,
)
db.add(grille)
db.flush()

total = 0
for ordre_th, (lib_th, bareme_th, pes) in enumerate(THEMES):
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

print("[OK] Grille R.482 C2 creee (id=%s) - total %s (attendu 100)" % (grille.id, total))
for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
    s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
    flag = "OK" if s == th.bareme_theme else "!!! ECART"
    print("   Theme '%s' : %s pts (declare %s, seuil %s) [%s]" % (th.libelle, s, th.bareme_theme, th.bareme_theme / 2, flag))
print("[OK] %s criteres eliminatoires" % len(ELIMINATOIRES))
db.close()