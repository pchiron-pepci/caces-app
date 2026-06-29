"""Peuple les 4 grilles d'evaluation pratique R.482 categorie A (base, multi-engins).
Un engin = une grille (variante PH/MB/CH/CP). PH = engin N°1 (toujours present, avec
le theme Operation de levage). MB/CH/CP = engin N°2 au choix.
Source : referentiel INRS R.482 A3/2/1 (verifie), cale sur les feuilles Excel OTC 'Pratique A *'.
Idempotent : cree la colonne `variante` si absente, puis supprime/recree les grilles A base.
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
    PointEvaluation.__table__, ItemPratique.__table__,
    CritereEliminatoire.__table__,
])

# --- Migration legere : colonne variante (idempotente, SQLite + PostgreSQL) ---
with engine.begin() as cx:
    try:
        cx.execute(text("ALTER TABLE grille_pratique ADD COLUMN variante VARCHAR(10)"))
        print("[OK] colonne 'variante' ajoutee")
    except Exception:
        print("[INFO] colonne 'variante' deja presente")

# ─────────────────────────────────────────────────────────────
# Briques communes (identiques aux 4 engins)
# Structure : (libelle_theme, bareme_theme, [ (num_pe, chapeau|None, [ (libelle, bareme|None) ]) ])
# ─────────────────────────────────────────────────────────────

def prise_de_poste():
    return ("Prise de poste et mise en service", 14, [
        ("1", None, [
            ("Verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :", 1),
            ("Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", None),
            ("Rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", 1),
            ("Proceder a une verification visuelle de l'engin de chantier", 1),
            ("Identifier les niveaux et les appoints journaliers", 1),
            ("Acceder au poste de conduite en securite (regle des 3 points d'appui)", 1),
            ("Effectuer les operations necessaires (reglages, nettoyage...) pour assurer la visibilite depuis le poste de conduite", 2),
            ("Effectuer le reglage du siege (position et suspension)", 1),
            ("Demarrer l'engin en respectant le mode operatoire prescrit", 2),
            ("Verifier le bon fonctionnement des organes de service et des differents indicateurs du tableau de bord", 1),
            ("Verifier le bon fonctionnement des dispositifs de securite", 2),
            ("Identifier la position de l'issue de secours et savoir expliquer sa mise en oeuvre", 1),
        ]),
    ])

def porte_engins():
    return ("Chargement dechargement sur un porte-engins", 16, [
        ("11", "Chargement de l'engin", [
            ("S'assurer de l'adequation de l'engin et du porte-engins a la manoeuvre prevue", 1),
            ("S'assurer que la position du vehicule est appropriee", 1),
            ("Verifier que les conditions permettant le chargement / dechargement sont remplies (espacement des rampes...)", 1),
            ("Monter l'engin sur le porte-engins dans le sens approprie", 2),
            ("Preparation au transport", 1),
            ("Positionner l'engin sur le porte-engins pour assurer l'equilibre et la stabilite", None),
            ("Mettre les equipements en position de transport", 1),
            ("Stabiliser l'engin (frein, stabilisateurs, cales...)", 1),
            ("Preparation de l'arrimage", 1),
            ("Identifier et designer les points d'arrimage sur le porte-engins", None),
            ("Identifier et designer les points d'arrimage sur l'engin", 1),
            ("Trouver le mode d'arrimage approprie (notice d'instructions...)", 1),
            ("S'assurer de l'adequation des moyens d'arrimage proposes", 1),
            ("Dechargement de l'engin", 1),
            ("S'assurer que l'environnement du porte-engins permet le dechargement", None),
            ("Positionner l'engin pour la descente", 1),
            ("Descendre l'engin en securite", 2),
        ]),
    ])

def fin_de_poste():
    return ("Fin de poste - maintenance", 8, [
        ("12", None, [
            ("Stationner l'engin en securite", 2),
            ("Positionner les equipements de facon appropriee", 1),
            ("Mettre en oeuvre les securites", 1),
            ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", 1),
            ("Quitter le poste de conduite en securite (regle des 3 points d'appui)", 2),
            ("Mettre l'engin a l'arret", 1),
        ]),
    ])

# Conduite : PH a un bareme reduit (22), MB/CH/CP = 38. Les libelles sont communs,
# seuls les baremes des items changent -> on parametre la liste des baremes.
def conduite(bareme_theme, baremes):
    # baremes = [circuler, verif_env, securite_pietons, stabilite, vitesses, freinage, aides, regles]
    return ("Conduite et circulation", bareme_theme, [
        ("2", "Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage (a evaluer en continu durant la totalite des epreuves)", [
            ("Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage", baremes[0]),
            ("Effectuer les manoeuvres avec souplesse et precision", None),
            ("Verifier au prealable l'environnement de travail", baremes[1]),
            ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", baremes[2]),
            ("Respecter les conditions de stabilite de l'engin", baremes[3]),
            ("Maitriser la selection des vitesses", baremes[4]),
            ("Utiliser correctement les dispositifs de freinage", baremes[5]),
            ("Recourir de facon appropriee aux aides a la conduite disponibles", baremes[6]),
            ("Respecter les regles et panneaux de circulation", baremes[7]),
        ]),
    ])

def levage():
    return ("Operation de levage", 16, [
        ("10", None, [
            ("Verifier la presence des dispositifs de securite", 4),
            ("S'assurer de l'adequation de l'engin a la manutention a realiser", 4),
            ("Determiner sur l'abaque de charge les charges / portees autorisees", 4),
            ("Effectuer l'operation de levage (prise et depose d'une charge au sol)", 4),
        ]),
    ])

# Travaux de base : PE specifiques par engin (PE 3-9 selon referentiel INRS)
TRAVAUX = {
    "PH": [
        ("3", None, [("Charger une unite de transport", 8)]),
        ("4", None, [("Effectuer une operation de deblai / remblai avec mise en stock", 8)]),
        ("5", None, [("Realiser une tranchee", 8)]),
    ],
    "MB": [
        ("6", None, [("Positionner l'engin pour le chargement", 8)]),
        ("7", None, [("Vider la benne", 8)]),
        ("9", None, [("Approcher un talus", 8)]),
    ],
    "CH": [
        ("3", None, [("Charger une unite de transport", 12)]),
        ("4", None, [("Effectuer une operation de deblai / remblai avec mise en stock", 12)]),
    ],
    "CP": [
        ("8", None, [("Compacter une plate-forme ou une piste", 12)]),
        ("9", None, [("Approcher un talus", 12)]),
    ],
}

# Conduite par engin (PH bareme reduit, autres = 38)
CONDUITE_PH = conduite(22, [4, 3, 3, 3, 1, 3, 3, 2])
CONDUITE_38 = conduite(38, [6, 5, 5, 5, 5, 5, 5, 2])

# Assemblage des 4 grilles (themes dans l'ordre INRS)
def themes_pour(variante):
    travaux = ("Travaux de base", 24, TRAVAUX[variante])
    if variante == "PH":
        return [prise_de_poste(), CONDUITE_PH, travaux, levage(), porte_engins(), fin_de_poste()]
    else:
        return [prise_de_poste(), CONDUITE_38, travaux, porte_engins(), fin_de_poste()]

ENGINS = [
    ("PH", "Pelle hydraulique compacte"),
    ("MB", "Motobasculeur compact"),
    ("CH", "Chargeuse compacte"),
    ("CP", "Compacteur compact"),
]

ELIMINATOIRES = [
    "Sauter de l'engin",
    "Ne pas garantir la securite des pietons",
    "Circuler avec une charge en hauteur",
    "Realiser une operation de levage avec un engin non equipe des dispositifs de securite appropries",
    "Quitter l'engin sans arreter le moteur",
]

db = SessionLocal()

# Suppression idempotente des grilles A base existantes
for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "A",
        GrillePratique.type == "base").all():
    db.delete(g)
db.commit()

for variante, lib_engin in ENGINS:
    grille = GrillePratique(
        recommandation="R.482", categorie="A", type="base", code_option=None,
        variante=variante, libelle="Engins compacts - %s" % lib_engin,
        ut=1.5, note_min=70, note_max=100, version="2025",
        ordre={"PH": 0, "MB": 1, "CH": 2, "CP": 3}[variante], actif=True,
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

    print("[OK] Grille A %s creee (id=%s) - total %s (attendu 100)" % (variante, grille.id, total))
    for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
        s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
        print("   Theme '%s' : %s pts (declare %s), seuil %s" % (th.libelle, s, th.bareme_theme, th.bareme_theme / 2))

db.close()
print("[OK] 4 grilles A (PH/MB/CH/CP) en base.")