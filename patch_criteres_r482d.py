"""Patch idempotent : remplit ItemPratique.critere_evaluation (colonne L Excel INRS)
sur la grille R.482 D (base compactage + options PE + TEL). Matching par libelle normalise.
Relancable sans risque.
"""
import os, unicodedata
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.grille_pratique import GrillePratique, ThemePratique, PointEvaluation, ItemPratique

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()


def norm(t):
    if t is None:
        return ""
    t = str(t).lower().replace("\u2019", "'").replace("\u2026", "...").strip()
    if t.startswith("* "):
        t = t[2:]
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    while "  " in t:
        t = t.replace("  ", " ")
    return t


CRITERES = {
    "base": [
        ('Verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :', 'Ne presente pas les documents reglementaires ou ne sait pas les exploiter (notice, rapport de verification)'),
        ("Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", 'Ne donne pas une justification correcte'),
        ("Rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", 'Ne comprend pas le rapport / Ne verifie pas la date du rapport / Ne verifie pas la conclusion du rapport'),
        ("Proceder a une verification visuelle de l'engin de chantier", 'Ne verifie pas un de ces elements : pneus / chenilles, articulations, axes et goupilles, flexibles hydrauliques, verins'),
        ('Identifier les niveaux et les appoints journaliers', "N'est pas capable d'expliquer les modalites d'approvisionnement en carburant et autres fluides / N'identifie pas les points de graissage essentiels"),
        ("Acceder au poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
        ('Effectuer les operations necessaires (reglages, nettoyage...) pour assurer la visibilite depuis le poste de conduite', "Selon les conditions : ne nettoie pas des vitres sales, ne les desembue pas, ne les deneige ou degivre pas, n'utilise pas l'essuie-glace, n'utilise pas l'eclairage exterieur"),
        ('Effectuer le reglage du siege (position et suspension)', 'Conduit avec un siege mal regle pour sa morphologie'),
        ("Demarrer l'engin en respectant le mode operatoire prescrit", "Ne parvient pas a demarrer l'engin sans aide (testeur ou notice)"),
        ('Verifier le bon fonctionnement des organes de service et des differents indicateurs du tableau de bord', "Oublie au moin un essai parmi : translation, direction, mouvements des extensions de l'engin dans toutes les directions / Ne comprend pas un symbole du tableau de bord"),
        ('Verifier le bon fonctionnement des dispositifs de securite', "Ne verifie pas un de ces elements (si equipe) : avertisseur sonore, eclairage, arret d'urgence, dispositif neutralisant les commandes / Ne fait pas un essai de freinage"),
        ("Identifier la position de l'issue de secours et savoir expliquer sa mise en oeuvre", "N'est pas capable d'expliquer comment sortir de l'engin si la sortie normale est inutilisable"),
        ('Circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage', 'Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle / Roule en dehors du chemin (talus, fosse...)'),
        ('Effectuer les manoeuvres avec souplesse et precision', 'Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle / Roule en dehors du chemin (talus, fosse...)'),
        ("Verifier au prealable l'environnement de travail", "N'identifie pas au prealable les points de vigilance du parcours"),
        ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", "Ne prend pas en compte un pieton dans ou a proximite de sa zone de travail (different de la faute eliminatoire, qui est le danger reel occasionne par un pieton proche de l'engin)"),
        ("Respecter les conditions de stabilite de l'engin", "Perd le controle du deplacement de l'engin du fait du relief, de l'etat du terrain, de la charge embarquee, de la vitesse de circulation, d'un freinage brusque, ou decolle les roues du sol"),
        ('Maitriser la selection des vitesses', 'Roule en sur-regime ou sous-regime significatif / Ne selectionne pas la bonne vitesse ou regime moteur selon les circonstances du deplacement'),
        ('Utiliser correctement les dispositifs de freinage', 'Freine avec retard ou trop brusquement, selon les circonstances du deplacement'),
        ('Recourir de facon appropriee aux aides a la conduite disponibles', "N'utilise pas les aides quand elles peuvent etre utiles (retroviseurs, motricite des roues...)"),
        ('Respecter les regles et panneaux de circulation', 'Ne respecte pas une interdiction ou une obligation / Franchit un balisage de la zone'),
        ('Charger une unite de transport', "Plus de 50 % des materiaux tombent a cote de l'unite de transport"),
        ('Effectuer une operation de deblai / remblai avec mise en stock', 'Creuse significativement le sol sous le tas de materiaux / Ne parvient pas a faire un tas homogene'),
        ('Realiser une tranchee', "La tranchee n'est pas rectiligne / Plus de 50 % du fond n'est pas plat / La largeur n'est pas reguliere / Les bords ne sont pas ebavures / Les materiaux ne sont pas deposes en cordon a 1 m / Le sol n'est pas aplani apres rebouchage"),
        ('Verifier la presence des dispositifs de securite', "Ne s'assure pas que l'engin est equipe pour le levage (oeillet, clapets de securite...)"),
        ("S'assurer de l'adequation de l'engin a la manutention a realiser", "Ne fait pas l'adequation en une fois pour toutes les charges ou par charge / Declare qu'une operation impossible est possible"),
        ("Determiner sur l'abaque de charge les charges / portees autorisees", "N'identifie pas une hauteur, une portee ou une capacite autorisees, selon des conditions proposees par le testeur"),
        ("Effectuer l'operation de levage (prise et depose d'une charge au sol)", "Les moyens d'elingage choisis sont inadequats / L'angle d'elingage n'est pas conforme a la tolerance de l'accessoire / La stabilite de l'engin est compromise lors du levage"),
        ("Stationner l'engin en securite", "Stationne l'engin de sorte qu'il y a un risque pour l'engin, pour les pietons ou pour la circulation sur le chantier"),
        ('Positionner les equipements de facon appropriee', 'Ne pose pas les equipements a plat au sol'),
        ('Mettre en oeuvre les securites', "Oublie d'enclencher au moins une securite (verrouillage des portes et capots, coupes-circuits, dispositif de neutralisation de commandes, frein de parc, coupe-batterie si necessaire...)"),
        ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", 'Ne respecte pas le mode operatoire / Ne retire pas la cle ou le dispositif antivol, le cas echeant'),
        ("Quitter le poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
        ("Mettre l'engin a l'arret", 'Oublie de fermer les vitres / Laisse les feux ou le gyrophare allumes'),
        ("Effectuer le compactage d'une plate-forme", "Plus de 50 % de la surface n'est pas plane"),
    ],
    "PE": [
        ("S'assurer de l'adequation de l'engin et du porte-engins a la manoeuvre prevue", 'Ne determine pas la capacite exacte du porte-engins / Choisit un porte-engins inadapte'),
        ("S'assurer que la position du vehicule est appropriee", "N'utilise pas efficacement l'espace de manoeuvre / Positionne le vehicule sur un sol inadapte"),
        ('Verifier que les conditions permettant le chargement / dechargement sont remplies (espacement des rampes...)', "Ne verifie pas le calage du porte-engins / Ne verifie pas l'espacement et la fixation des rampes"),
        ("Monter l'engin sur le porte-engins dans le sens approprie", 'Ne monte pas dans le sens indique par le constructeur / Met en danger par une trajectoire ou une vitesse inadaptee'),
        ("Positionner l'engin sur le porte-engins pour assurer l'equilibre et la stabilite", "Le chargement n'est pas equilibre par rapport aux essieux"),
        ('Mettre les equipements en position de transport', 'Ne coupe pas les energies'),
        ("Stabiliser l'engin (frein, stabilisateurs, cales...)", "L'engin peut glisser et se deplacer pendant le transport"),
        ("Identifier et designer les points d'arrimage sur le porte-engins", "Les points designes ne permettent pas l'immobilisation de l'engin"),
        ("Identifier et designer les points d'arrimage sur l'engin", "Les points designes ne permettent pas l'immobilisation de l'engin"),
        ("Trouver le mode d'arrimage approprie (notice d'instructions...)", "Ne trouve pas le mode d'arrimage dans la notice"),
        ("S'assurer de l'adequation des moyens d'arrimage proposes", 'Les moyens choisis ne sont pas adequats'),
        ("S'assurer que l'environnement du porte-engins permet le dechargement", "Ne verifie pas l'absence de coactivite"),
        ("Positionner l'engin pour la descente", "L'engin n'est pas dans l'axe des rampes"),
        ("Descendre l'engin en securite", 'Ne parvient pas a adapter ses trajectoires et sa vitesse a la descente'),
    ],
    "TEL": [
        ("Verifier le fonctionnement de la telecommande (equipements de transmission, boutons, voyants...), notamment l'arret d'urgence et la cle de condamnation", "Ne controle pas la transmission / N'essaie pas l'arret d'urgence ou la cle de condamnation"),
        ("Verifier l'impossibilite de fonctionnement simultane de la telecommande et du poste de conduite principal", "Ne procede pas a l'essai depuis le poste de conduite principal"),
        ("Enumerer les risques lies a l'utilisation de la telecommande", "N'est pas capable de citer au moins quatre risques lies a l'utilisation de la telecommande"),
        ("Savoir se positionner par rapport a la zone de travail et d'evolution de l'engin", "Lors des essais de fonctionnement, ne se positionne pas correctement par rapport a la zone d'evolution de l'engin"),
        ('Au moyen de la telecommande, circuler en marche avant / en marche arriere, en ligne droite / en virage', 'Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle'),
        ("Verifier au prealable l'environnement de travail", "N'identifie pas au prealable les points de vigilance du parcours"),
        ('Se positionner pour avoir la meilleure vision de la manoeuvre et de son environnement, tout en restant hors de la zone de risque', "Ne conserve pas une vision degagee de l'engin et de son environnement / Se place dans la zone de risque"),
        ('Garantir la securite des pietons', 'Ne prend pas en compte un pieton dans ou a proximite de sa zone de travail'),
        ('Effectuer les manoeuvres avec souplesse et precision', 'Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle'),
        ("Au moyen de la telecommande, realiser les travaux pour lesquels l'engin est concu", "Se referer aux criteres definis dans la grille d'evaluation de la categorie (PE 3, 4, 5)"),
    ],
}


def grilles_du_bloc(bloc):
    if bloc == "base":
        return db.query(GrillePratique).filter(
            GrillePratique.recommandation == "R.482",
            GrillePratique.categorie == "D",
            GrillePratique.type == "base").all()
    return db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "D",
        GrillePratique.type == "option",
        GrillePratique.code_option == bloc).all()


total_ok = 0
total_miss = 0
for bloc, paires in CRITERES.items():
    crit_map = {norm(lib): ev for lib, ev in paires}
    for grille in grilles_du_bloc(bloc):
        items = db.query(ItemPratique).join(
            PointEvaluation, ItemPratique.pe_id == PointEvaluation.id).join(
            ThemePratique, PointEvaluation.theme_id == ThemePratique.id).filter(
            ThemePratique.grille_id == grille.id).all()
        for it in items:
            ev = crit_map.get(norm(it.libelle))
            if ev:
                it.critere_evaluation = ev
                total_ok += 1
            elif (not it.descriptif_seul) and it.bareme_max:
                total_miss += 1
                print("[MISS %s] %s" % (bloc, it.libelle[:60]))
    db.commit()

print("[OK] %d criteres ecrits, %d lignes notees sans critere" % (total_ok, total_miss))
db.close()