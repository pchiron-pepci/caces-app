"""Peuple la grille d'evaluation pratique R.482 categorie C1 (base), 2 variantes d'engin :
- CH = Chargeuse (chargement pur, pas de levage) : Prise/16 + Conduite/32 + Travaux/40 + Fin/12 = 100
- CP = Chargeuse-pelleteuse (mixte, avec levage) : Prise/16 + Conduite/24 + Travaux/32 + Levage/16 + Fin/12 = 100
Source : referentiel INRS R.482 A3/2, cale sur les feuilles Excel OTC 'Pratique C1 - CH' et '- CP'.
Idempotent. C1 base = 1,0 UT. Options PE/TEL facultatives (script separe).
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

# Colonne variante (idempotente)
with engine.begin() as cx:
    try:
        cx.execute(text("ALTER TABLE grille_pratique ADD COLUMN variante VARCHAR(10)"))
        print("[OK] colonne 'variante' ajoutee")
    except Exception:
        print("[INFO] colonne 'variante' deja presente")


# ---- Themes communs ----
def prise_de_poste():
    return ("Prise de poste et mise en service", 16, [
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
    ])


def conduite(bareme_theme, bareme_circuler, bareme_vitesses, bareme_freinage):
    return ("Conduite et circulation", bareme_theme, [
        ("2", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage", bareme_circuler),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", 3),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", 3),
            ("Respecter les conditions de stabilite de l'engin", 3),
            ("Maitriser la selection des vitesses", bareme_vitesses),
            ("Utiliser correctement les dispositifs de freinage", bareme_freinage),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", 3),
            ("Respecter les regles et panneaux de circulation", 2),
        ]),
    ])


def levage():
    return ("Operation de levage", 16, [
        ("6", None, [
            ("Verifier la presence des dispositifs de securite", 4),
            ("S'assurer de l'adequation de l'engin a la manutention a realiser", 4),
            ("Determiner sur l'abaque de charge les charges / portees autorisees", 4),
            ("Effectuer l'operation de levage (prise et depose d'une charge au sol)", 4),
        ]),
    ])


def fin_de_poste():
    return ("Operation de fin de poste - maintenance", 12, [
        ("7", None, [
            ("Stationner l'engin en securite", 2),
            ("Positionner les equipements de facon appropriee", 2),
            ("Mettre en oeuvre les securites", 2),
            ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", 2),
            ("Quitter le poste de conduite en securite (regle des 3 points d'appui)", 2),
            ("Mettre l'engin a l'arret", 2),
        ]),
    ])


# ---- Themes "Travaux de base" specifiques a chaque variante ----
def travaux_CH():
    # Chargeuse : charger /20 + deblai-remblai /20 = /40
    return ("Travaux de base", 40, [
        ("3", None, [("Charger une unite de transport", 20)]),
        ("4", None, [("Effectuer une operation de deblai / remblai avec mise en stock", 20)]),
    ])


def travaux_CP():
    # Chargeuse-pelleteuse : charger /16 + tranchee /16 = /32
    return ("Travaux de base", 32, [
        ("3", None, [("Charger une unite de transport", 16)]),
        ("5", None, [("Realiser une tranchee", 16)]),
    ])


def themes_pour(variante):
    if variante == "CH":
        # Chargeuse : conduite /32 (circuler 10, vitesses 3, freinage 5), pas de levage
        return [prise_de_poste(), conduite(32, 10, 3, 5), travaux_CH(), fin_de_poste()]
    else:  # CP
        # Chargeuse-pelleteuse : conduite /24 (circuler 6, vitesses 1, freinage 3), avec levage /16
        return [prise_de_poste(), conduite(24, 6, 1, 3), travaux_CP(), levage(), fin_de_poste()]


ENGINS = [
    ("CH", "Chargeuse"),
    ("CP", "Chargeuse-pelleteuse"),
]

ELIMINATOIRES = [
    "Sauter de l'engin",
    "Ne pas garantir la securite des pietons",
    "Circuler avec une charge en hauteur",
    "Realiser une operation de levage avec un engin non equipe des dispositifs de securite appropries",
    "Quitter l'engin sans arreter le moteur",
]

db = SessionLocal()

# Suppression idempotente des grilles C1 base existantes
for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "C1",
        GrillePratique.type == "base").all():
    db.delete(g)
db.commit()

for variante, lib_engin in ENGINS:
    grille = GrillePratique(
        recommandation="R.482", categorie="C1", type="base", code_option=None,
        variante=variante, libelle="Engins de chargement a deplacement alternatif - %s" % lib_engin,
        ut=1.0, note_min=70, note_max=100, version="2025",
        ordre={"CH": 0, "CP": 1}[variante], actif=True,
    )
    db.add(grille)
    db.flush()

    total = 0
    for ordre_th, (lib_th, bareme_th, pes) in enumerate(themes_pour(variante)):
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

    print("[OK] Grille C1 %s creee (id=%s) - total %s (attendu 100)" % (variante, grille.id, total))
    for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
        s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
        flag = "OK" if s == th.bareme_theme else "!!! ECART"
        print("   Theme '%s' : %s pts (declare %s, seuil %s) [%s]" % (th.libelle, s, th.bareme_theme, th.bareme_theme / 2, flag))

db.close()
print("[OK] 2 grilles C1 (CH/CP) en base.")