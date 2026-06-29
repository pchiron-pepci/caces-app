"""Peuple la grille d'evaluation pratique de l'OPTION Telecommande (TEL) de R.482 cat A.
0,5 UT, note_max 50, seuil 35. Identique au referentiel INRS (meme grille que cat F).
La cat A n'a PAS d'option Porte-engins separee : le porte-engins est inclus dans la base. Idempotent.
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
Base.metadata.create_all(bind=engine, tables=[
    GrillePratique.__table__, ThemePratique.__table__,
    PointEvaluation.__table__, ItemPratique.__table__,
])

OPTION = ("TEL", "Telecommande", 1, [
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
])

db = SessionLocal()

code, libelle, ordre_opt, themes = OPTION

for g in db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "A",
        GrillePratique.type == "option",
        GrillePratique.code_option == code).all():
    db.delete(g)
db.commit()

grille = GrillePratique(
    recommandation="R.482", categorie="A", type="option", code_option=code,
    variante=None, libelle=libelle, ut=0.5, note_min=35, note_max=50,
    version="2025", ordre=ordre_opt, actif=True,
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

print("[OK] Option A TEL creee (id=%s) - total %s (attendu 50)" % (grille.id, total))
for th in db.query(ThemePratique).filter(ThemePratique.grille_id == grille.id).order_by(ThemePratique.ordre):
    s = sum(it.bareme_max for pe in th.points for it in pe.items if it.bareme_max)
    print("   Theme '%s' : %s pts (declare %s), seuil %s" % (th.libelle, s, th.bareme_theme, th.bareme_theme / 2))
db.close()