"""Peuple les grilles d'evaluation pratique des OPTIONS de R.482 F :
Porte-engins (PE) et Telecommande (TEL), 0,5 UT chacune, note_max 50, seuil 35.
Source : feuille Excel OTC 'Pratique F'. Idempotent.
"""
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
Base.metadata.create_all(bind=engine)

OPTIONS = [
    ("PE", "Porte-engins", 1, [
        ("Chargement de l'engin", 15, [
            ("1", None, [
                ("S'assurer de l'adequation de l'engin et du porte-engins a la manoeuvre prevue", 3),
                ("S'assurer que la position du vehicule est appropriee", 3),
                ("Verifier que les conditions permettant le chargement / dechargement sont remplies (espacement des rampes...)", 3),
                ("Monter l'engin sur le porte-engins dans le sens approprie", 6),
            ]),
        ]),
        ("Preparation au transport", 10, [
            ("2", None, [
                ("Positionner l'engin sur le porte-engins pour assurer l'equilibre et la stabilite", 4),
                ("Mettre les equipements en position de transport", 3),
                ("Stabiliser l'engin (frein, stabilisateurs, cales...)", 3),
            ]),
        ]),
        ("Preparation de l'arrimage", 10, [
            ("3", None, [
                ("Identifier et designer les points d'arrimage sur le porte-engins", 2),
                ("Identifier et designer les points d'arrimage sur l'engin", 2),
                ("Trouver le mode d'arrimage approprie (notice d'instructions...)", 3),
                ("S'assurer de l'adequation des moyens d'arrimage proposes", 3),
            ]),
        ]),
        ("Dechargement de l'engin", 15, [
            ("4", None, [
                ("S'assurer que l'environnement du porte-engins permet le dechargement", 3),
                ("Positionner l'engin pour la descente", 5),
                ("Descendre l'engin en securite", 7),
            ]),
        ]),
    ]),
    ("TEL", "Telecommande", 2, [
        ("Verification et prise de poste", 20, [
            ("1", None, [
                ("Verifier le fonctionnement de la telecommande (equipements de transmission, boutons, voyants...), notamment l'arret d'urgence et la cle de condamnation", 6),
                ("Verifier l'impossibilite de fonctionnement simultane de la telecommande et du poste de conduite principal", 4),
                ("Enumerer les risques lies a l'utilisation de la telecommande", 6),
                ("Savoir se positionner par rapport a la zone de travail et d'evolution de l'engin", 4),
            ]),
        ]),
        ("Manoeuvres", 30, [
            ("2", "Au moyen de la telecommande, circuler en marche avant / en marche arriere, en ligne droite / en virage (a evaluer en continu)", [
                ("Au moyen de la telecommande, circuler en marche avant / en marche arriere, en ligne droite / en virage", 3),
                ("Verifier au prealable l'environnement de travail", None),
                ("Se positionner pour avoir la meilleure vision de la manoeuvre et de son environnement, tout en restant hors de la zone de risque", 4),
                ("Garantir la securite des pietons", 4),
                ("Effectuer les manoeuvres avec souplesse et precision", 4),
            ]),
            ("3", None, [
                ("Au moyen de la telecommande, realiser les travaux pour lesquels l'engin est concu", 15),
            ]),
        ]),
    ]),
]

db = SessionLocal()

for code, libelle, ordre_opt, themes in OPTIONS:
    for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "F",
        GrillePratique.type == "option",
        GrillePratique.code_option == code,
    ).all():
        db.delete(g)
    db.commit()

    grille = GrillePratique(
        recommandation="R.482", categorie="F", type="option", code_option=code,
        libelle=libelle, ut=0.5, note_min=35, note_max=50, version="2025",
        ordre=ordre_opt, actif=True,
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
    db.commit()
    print("[OK] Option %s '%s' creee (id=%s) - total %s (attendu 50)" % (code, libelle, grille.id, total))
    for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
        s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
        print("   Theme '%s' : %s pts (declare %s), %s PE, seuil %s" % (
            th.libelle, s, th.bareme_theme, len(th.points), th.bareme_theme / 2))

db.close()
