"""Patch idempotent : remplit ItemPratique.critere_evaluation (colonne L Excel INRS)
sur les grilles R.482 categorie A (4 engins base + option TEL) deja peuplees.
Matching par libelle normalise (accents + ligature oe). Relancable sans risque."""
import os, unicodedata
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.grille_pratique import GrillePratique, ThemePratique, PointEvaluation, ItemPratique

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def norm(t):
    if t is None: return ""
    t = str(t).lower().replace("\u2019","'").replace("\u2026","...").replace("\n"," ")
    t = t.replace("\u0153","oe").replace("\u00e6","ae")
    t = t.strip()
    if t.startswith("* "): t = t[2:]
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    while "  " in t: t = t.replace("  ", " ")
    return t

CRITERES = [
    ("notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", 'Ne donne pas une justification correcte'),
    ("rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", 'Ne comprend pas le rapport / Ne vérifie pas la date du rapport / Ne vérifie pas la conclusion du rapport'),
    ("proceder a une verification visuelle de l'engin de chantier", 'Ne vérifie pas un de ces éléments : pneus / chenilles, articulations, axes et goupilles, flexibles hydrauliques, vérins'),
    ('identifier les niveaux et les appoints journaliers', "N'est pas capable d'expliquer les modalités d'approvisionnement en carburant et autres fluides /  N'identifie pas les points de graissage essentiels"),
    ("acceder au poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
    ('effectuer les operations necessaires (reglages, nettoyage...) pour assurer la visibilite depuis le poste de conduite', "Selon les conditions : ne nettoie pas des vitres sales, ne les désembue pas, ne les déneige ou dégivre pas, n'utilise pas l'essuie-glace, n'utilise pas l'éclairage extérieur"),
    ('effectuer le reglage du siege (position et suspension)', 'Conduit avec un siège mal réglé pour sa morphologie'),
    ("demarrer l'engin en respectant le mode operatoire prescrit", "Ne parvient pas à démarrer l'engin sans aide (testeur ou notice)"),
    ('verifier le bon fonctionnement des organes de service et des differents indicateurs du tableau de bord', "Oublie au moin un essai parmi : translation, direction, mouvements des extensions de l'engin dans toutes les directions / Ne comprend pas un symbole du tableau de bord"),
    ('verifier le bon fonctionnement des dispositifs de securite', "Ne vérifie pas un de ces éléments (si équipé) : avertisseur sonore, éclairage, arrêt d'urgence, dispositif neutralisant les commandes / Ne fait pas un essai de freinage"),
    ("identifier la position de l'issue de secours et savoir expliquer sa mise en oeuvre", "N'est pas capable d'expliquer comment sortir de l'engin si la sortie normale est inutilisable"),
    ('effectuer les manoeuvres avec souplesse et precision', 'Donne des à-coups injustifiés / Ne parvient pas à adapter ses trajectoires / Heurte un obstacle / Roule en dehors du chemin (talus, fossé…)'),
    ("verifier au prealable l'environnement de travail", "N'identifie pas au préalable les points de vigilance du parcours"),
    ("garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore...)", "Ne prend pas en compte un piéton dans ou à proximité de sa zone de travail (différent de la faute éliminatoire, qui est le danger réel occasionné par un piéton proche de l'engin)"),
    ("respecter les conditions de stabilite de l'engin", "Perd le contrôle du déplacement de l'engin du fait du relief, de l'état du terrain, de la charge embarquée, de la vitesse de circulation, d'un freinage brusque, ou décolle les roues du sol"),
    ('maitriser la selection des vitesses', 'Roule en sur-régime ou sous-régime significatif / Ne sélectionne pas la bonne vitesse ou régime moteur selon les circonstances du déplacement'),
    ('utiliser correctement les dispositifs de freinage', 'Freine avec retard ou trop brusquement, selon les circonstances du déplacement'),
    ('recourir de facon appropriee aux aides a la conduite disponibles', "N'utilise pas les aides quand elles peuvent être utiles (rétroviseurs, motricité des roues…)"),
    ('respecter les regles et panneaux de circulation', 'Ne respecte pas une interdiction ou une obligation / Franchit un balisage de la zone'),
    ('charger une unite de transport', "Plus de 50 % des matériaux tombent à côté de l'unité de transport"),
    ('effectuer une operation de deblai / remblai avec mise en stock', 'Creuse significativement le sol sous le tas de matériaux / Ne parvient pas à faire un tas homogène'),
    ('realiser une tranchee', "La tranchée n'est pas rectiligne / Plus de 50 % du fond n'est pas plat / La largeur n'est pas régulière / Les bords ne sont pas ébavurés / Les matériaux ne sont pas déposés en cordon à 1 m / Le sol n'est pas aplani après rebouchage"),
    ('verifier la presence des dispositifs de securite', "Ne s'assure pas que l'engin est équipé pour le levage (œillet, clapets de sécurité…)"),
    ("s'assurer de l'adequation de l'engin a la manutention a realiser", "Ne fait pas l'adéquation en une fois pour toutes les charges ou par charge / Déclare qu'une opération impossible est possible"),
    ("determiner sur l'abaque de charge les charges / portees autorisees", "N'identifie pas une hauteur, une portée ou une capacité autorisées, selon des conditions proposées par le testeur"),
    ("effectuer l'operation de levage (prise et depose d'une charge au sol)", "Les moyens d'élingage choisis sont inadéquats / L'angle d'élingage n'est pas conforme à la tolérance de l'accessoire / La satbilité de l'engin est compromise lors du levage"),
    ("s'assurer de l'adequation de l'engin et du porte-engins a la manoeuvre prevue", 'Ne détermine pas la capacité exacte du porte-engins'),
    ("s'assurer que la position du vehiule est appropriee", "N'utilise pas efficacement l'espace de manœuvre devant les rampes"),
    ('verifier que les conditions permettant le chargement / dechargement sont remplies (espacement des rampes...)', "Ne vérifie pas le calage du porte-engins / Ne vérifie pas l'état du plancher et des rampes (le cas échéant)"),
    ("monter l'engin sur le porte-engins dans le sens approprie", 'Ne monte pas dans le sens indiqué par le fabricant / Ne parvient pas à adapter ses trajectoires / Perd le contrôle lors de la montée'),
    ("positionner l'engin sur le porte-engins pour assurer l'equilibre et la stabilite", "Le chargement n'est pas équilibré par rapport à l'axe longitudinal et transversal"),
    ('mettre les equipements en position de transport', 'Ne coupe pas les énergies'),
    ("stabiliser l'engin (frein, stabilisateurs, cales...)", "L'engin peut glisser et se déplacer pendant le transport"),
    ("identifier et designer les points d'arrimage sur le porte-engins", "Les points désignés ne permettent pas l'arrimage selon les préconisations du fabricant ou les règles de l'art"),
    ("identifier et designer les points d'arrimage sur l'engin", "Les points désignés ne permettent pas l'arrimage selon les préconisations du fabricant ou les règles de l'art"),
    ("trouver le mode d'arrimage approprie (notice d'instructions...)", "Ne trouve pas le mode d'arrimage dans la notice (s'il existe) ou ne propose pas une solution d'arrimage sûre"),
    ("s'assurer de l'adequation des moyens d'arrimage proposes", 'Les moyens choisis ne sont pas adéquats'),
    ("s'assurer que l'environnement du porte-engins permet le dechargement", "Ne vérifie pas l'absence de coactivité"),
    ("positionner l'engin pour la descente", "L'engin n'est pas dans l'axe des rampes"),
    ("descendre l'engin en securite", 'Ne parvient pas à adapter ses trajectoires / Perd le contrôle lors de la descente'),
    ("stationner l'engin en securite", "Stationne l'engin de sorte qu'il y a un risque pour l'engin, pour les piétons ou pour la circulation sur le chantier"),
    ('positionner les equipements de facon appropriee', 'Ne pose pas les équipements à plat au sol'),
    ('mettre en oeuvre les securites', "Oublie d'enclencher au moins une sécurité (verrouillage des portes et capots, coupes-circuits, dispositif de neutralisation de commandes, frein de parc, coupe-batterie si nécessaire…)"),
    ("arreter le moteur de l'engin en respectant le mode operatoire prescrit", 'Ne respecte pas le mode opératoire / Ne retire pas la clé ou le dispositif antivol, le cas échéant'),
    ("quitter le poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
    ("mettre l'engin a l'arret", 'Oublie de fermer les vitres / Laisse les feux ou le gyrophare allumés'),
    ("verifier le fonctionnement de la telecommande (equipements de transmission, boutons, voyants...), notamment l'arret d'urgence et la cle de condamnation", "Ne contrôle pas la transmission / N'essaie pas l'arrêt d'urgence / Ne vérifie pas le fonctionnement du dispositif de condamnation (s'il existe)"),
    ("verifier l'impossibilite de fonctionnement simultane de la telecommande et du poste de conduite principal", "Ne procède pas à l'essai depuis le poste de conduite principal, après avoir mis en service la télécommande"),
    ("enumerer les risques lies a l'utilisation de la telecommande", "N'est pas capable de citer au moins quatre risques"),
    ("savoir se positionner par rapport a la zone de travail et d'evolution de l'engin", "Lors des essais de fonctionnement, ne se tient pas de façon à voir le résultat des essais, tout en étant suffisamment éloigné des parties mobiles de l'engin"),
    ('se positionner pour avoir la meilleure vision de la manoeuvre et de son environnement, tout en restant hors de la zone de risque', "Ne conserve pas une vision dégagée de l'engin et de la zone, en permanence / Se tient dans la zone immédiate de manœuvre de l'engin, ou dans le rayon d'action des équipements"),
    ('garantir la securite des pietons', "Ne prend pas en compte un piéton dans ou à proximité de sa zone de travail (différent de la faute éliminatoire, qui est le danger réel occasionné par un piéton proche de l'engin)"),
    ("au moyen de la telecommande, realiser les travaux pour lesquels l'engin est concu", 'Se référer aux critères définis dans la grille d’évaluation de la catégorie (PE 3, 4 et 5)'),
    ("positionner l'engin pour le chargement", "Le tombereau n'est pas placé de sorte que l'engin de chargement puisse répartir les matériaux dans la benne"),
    ('vider la benne', 'Ne vide pas la benne en totalité / Une partie des matériaux est déchargée en dehors de la zone prévue'),
    ('approcher un talus', 'Ne maintient pas une trajectoire parallèle au talus (distance environ 30 cm)'),
    ('compacter une plate-forme ou une piste', "Plus de 50 % de la surface n'est pas plane"),
    ('verifier la presence et la validite des documents reglementaires suivants, et savoir les exploiter :', 'Ne fait pas une verification visuelle / Ne fait pas des essais statiques'),
    ('circuler a vide et en charge, en marche avant / en marche arriere, en ligne droite / en virage', "Abime le materiel / Mise en danger necessitant l'intervention du testeur"),
    ("s'assurer que la position du vehicule est appropriee", "N'utilise pas efficacement l'espace de manoeuvre devant les rampes"),
    ('preparation au transport', "Le chargement n'est pas equilibre par rapport a l'axe longitudinal et transversal"),
    ("preparation de l'arrimage", "Les points designes ne permettent pas l'arrimage selon les preconisations du fabricant ou les regles de l'art"),
    ("dechargement de l'engin", "Ne verifie pas l'absence de coactivite"),
    ('au moyen de la telecommande, circuler en marche avant / en marche arriere, en ligne droite / en virage', "Abime le materiel / Mise en danger necessitant l'intervention du testeur"),
]
crit_map = {k: ev for k, ev in CRITERES}

grilles = db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.482",
    GrillePratique.categorie == "A").all()

total_ok = 0; total_miss = 0
for grille in grilles:
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
            print("[MISS %s/%s] %s" % (grille.variante, grille.code_option, it.libelle[:55]))
    db.commit()

print("[OK] %d criteres ecrits, %d lignes notees sans critere" % (total_ok, total_miss))
db.close()