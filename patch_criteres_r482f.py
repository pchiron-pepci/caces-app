"""Patch idempotent : remplit ItemPratique.critere_evaluation (colonne L Excel INRS)
sur la grille R.482 F (base + options PE + TEL) deja peuplee. Matching par libelle.
Ne recree rien. Relancable sans risque."""
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
    t = str(t).lower().replace("’", "'").strip()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    while "  " in t:
        t = t.replace("  ", " ")
    return t

CRITERES = {
    "base": [
        ("* Notice d'instructions (justifier une interdiction d'emploi ou une regle d'utilisation)", "Ne donne pas une justification correcte"),
        ("* Rapport de verification generale periodique, de mise ou de remise en service (verifier l'absence d'observation ou de restriction d'usage)", "Ne comprend pas le rapport / Ne verifie pas la date du rapport / Ne verifie pas la conclusion du rapport"),
        ("Proceder a une verification visuelle de l'engin de chantier", "Ne verifie pas un de ces elements : pneus / chenilles, articulations, axes et goupilles, flexibles hydrauliques, verins"),
        ("Identifier les niveaux et les appoints journaliers", "N'est pas capable d'expliquer les modalites d'approvisionnement en carburant et autres fluides / N'identifie pas les points de graissage essentiels"),
        ("Acceder au poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
        ("Effectuer les operations necessaires (reglages, nettoyage…) pour assurer la visibilite depuis le poste de conduite", "Selon les conditions : ne nettoie pas des vitres sales, ne les desembue pas, ne les deneige ou degivre pas, n'utilise pas l'essuie-glace, n'utilise pas l'eclairage exterieur"),
        ("Effectuer le reglage du siege (position et suspension)", "Conduit avec un siege mal regle pour sa morphologie"),
        ("Demarrer l'engin en respectant le mode operatoire prescrit", "Ne parvient pas a demarrer l'engin sans aide (testeur ou notice)"),
        ("Verifier le bon fonctionnement des organes de service et des differents indicateurs du tableau de bord", "Oublie au moin un essai parmi : translation, direction, mouvements des extensions de l'engin dans toutes les directions / Ne comprend pas un symbole du tableau de bord"),
        ("Verifier le bon fonctionnement des dispositifs de securite", "Ne verifie pas un de ces elements (si equipe) : avertisseur sonore, eclairage, arret d'urgence, dispositif neutralisant les commandes / Ne fait pas un essai de freinage"),
        ("Identifier la position de l'issue de secours et savoir expliquer sa mise en oeuvre", "N'est pas capable d'expliquer comment sortir de l'engin si la sortie normale est inutilisable"),
        ("Prendre connaissance des abaques de charge et savoir determiner la capacite du chariot en fonction de la hauteur et de la portee, dans les differentes configurations (sur pneumatiques, sur stabilisateurs…)", "N'identifie pas une hauteur, une portee ou une capacite autorisees, selon des conditions proposees par le testeur (avec et sans stabilisateurs) / Ne trouve pas la capacite nominale du chariot"),
        ("S'assurer de l'adequation du chariot a la manutention a realiser (capacite, hauteur, portee…)", "Se trompe ou ne realise pas l'examen d'adequation des charges devant etre chargees sur le vehicule"),
        ("Verifier que la configuration de la charge (support, nature, homogeneite, stabilite…) est compatible avec le levage", "Ne verifie pas l'etat d'une des charges devant etre manutentionnees"),
        ("Effectuer les manoeuvres avec souplesse et precision", "Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle / Roule en dehors du chemin (talus, fosse…)"),
        ("Verifier au prealable l'environnement de travail", "N'identifie pas au prealable les points de vigilance du parcours"),
        ("Garantir la securite des pietons (vision en marche arriere, utilisation correcte de l'avertisseur sonore…)", "Ne prend pas en compte un pieton dans ou a proximite de sa zone de travail (different de la faute eliminatoire, qui est le danger reel occasionne par un pieton proche de l'engin)"),
        ("Respecter les conditions de stabilite de l'engin", "Perd le controle du deplacement de l'engin du fait du relief, de l'etat du terrain, de la charge embarquee, de la vitesse de circulation, d'un freinage brusque, ou decolle les roues du sol"),
        ("Maitriser la selection des vitesses", "Roule en sur-regime ou sous-regime significatif / Ne selectionne pas la bonne vitesse ou regime moteur selon les circonstances du deplacement"),
        ("Utiliser correctement les dispositifs de freinage", "Freine avec retard ou trop brusquement, selon les circonstances du deplacement"),
        ("Recourir de facon appropriee aux aides a la conduite disponibles", "N'utilise pas les aides quand elles peuvent etre utiles (retroviseurs, motricite des roues…)"),
        ("Respecter les regles et panneaux de circulation", "Ne respecte pas une interdiction ou une obligation / Franchit un balisage de la zone"),
        ("Charger et decharger un camion en utilisant au moins trois charges", "Ne verifie pas ou ne cale pas le vehicule / N'estime pas correctement la capacite autorisee en charge du vehicule / Heurte la charge ou le vehicule / La fourche frotte sur les charges pendant le retrait de la fourche / Le chargement n'est pas equilibre par rapport a l'axe longitudinal et transversal / Les charges depassent du vehicule"),
        ("Manutentionner une charge longue", "La charge touche le sol ou un obstacle pendant son transport / La charge est instable / La charge tombe de la fourche / S'y reprend a 3 fois ou plus pour prendre ou deposer la charge au sol"),
        ("Manutentionner une charge lourde (minimum 50 % de la capacite du chariot)", "Heurte la charge / La charge est a plus de 20 cm du talon de fourche / Circule fourche a plus d'1 m du sol / S'y reprend a 3 fois ou plus pour prendre ou deposer la charge au sol"),
        ("Manutentionner une charge complexe", "La charge touche le sol pendant son transport / La charge est instable / La charge tombe de la fourche / S'y reprend a 3 fois ou plus pour prendre ou deposer la charge au sol"),
        ("Stationner l'engin en securite", "Stationne l'engin de sorte qu'il y a un risque pour l'engin, pour les pietons ou pour la circulation sur le chantier"),
        ("Positionner les equipements de facon appropriee", "Ne pose pas les equipements a plat au sol"),
        ("Mettre en oeuvre les securites", "Oublie d'enclencher au moins une securite (verrouillage des portes et capots, coupes-circuits, dispositif de neutralisation de commandes, frein de parc, coupe-batterie si necessaire…)"),
        ("Arreter le moteur de l'engin en respectant le mode operatoire prescrit", "Ne respecte pas le mode operatoire / Ne retire pas la cle ou le dispositif antivol, le cas echeant"),
        ("Quitter le poste de conduite en securite (regle des 3 points d'appui)", "Ne prend pas trois points d'appui"),
        ("Mettre l'engin a l'arret", "Oublie de fermer les vitres / Laisse les feux ou le gyrophare allumes"),
    ],
    "PE": [
        ("S'assurer de l'adequation de l'engin et du porte-engins a la manoeuvre prevue", "Ne determine pas la capacite exacte du porte-engins"),
        ("S'assurer que la position du vehicule est appropriee", "N'utilise pas efficacement l'espace de manoeuvre devant les rampes"),
        ("Verifier que les conditions permettant le chargement / dechargement sont remplies (espacement des rampes…)", "Ne verifie pas le calage du porte-engins / Ne verifie pas l'etat du plancher et des rampes (le cas echeant)"),
        ("Monter l'engin sur le porte-engins dans le sens approprie", "Ne monte pas dans le sens indique par le fabricant / Ne parvient pas a adapter ses trajectoires / Perd le controle lors de la montee"),
        ("Positionner l'engin sur le porte-engins pour assurer l'equilibre et la stabilite", "Le chargement n'est pas equilibre par rapport a l'axe longitudinal et transversal"),
        ("Mettre les equipements en position de transport", "Ne coupe pas les energies"),
        ("Stabiliser l'engin (frein, stabilisateurs, cales…)", "L'engin peut glisser et se deplacer pendant le transport"),
        ("Identifier et designer les points d'arrimage sur le porte-engins", "Les points designes ne permettent pas l'arrimage selon les preconisations du fabricant ou les regles de l'art"),
        ("Identifier et designer les points d'arrimage sur l'engin", "Les points designes ne permettent pas l'arrimage selon les preconisations du fabricant ou les regles de l'art"),
        ("Trouver le mode d'arrimage approprie (notice d'instructions…)", "Ne trouve pas le mode d'arrimage dans la notice (s'il existe) ou ne propose pas une solution d'arrimage sure"),
        ("S'assurer de l'adequation des moyens d'arrimage proposes", "Les moyens choisis ne sont pas adequats"),
        ("S'assurer que l'environnement du porte-engins permet le dechargement", "Ne verifie pas l'absence de coactivite"),
        ("Positionner l'engin pour la descente", "L'engin n'est pas dans l'axe des rampes"),
        ("Descendre l'engin en securite", "Ne parvient pas a adapter ses trajectoires / Perd le controle lors de la descente"),
    ],
    "TEL": [
        ("Verifier le fonctionnement de la telecommande (equipements de transmission, boutons, voyants…), notamment l'arret d'urgence et la cle de condamnation", "Ne controle pas la transmission / N'essaie pas l'arret d'urgence / Ne verifie pas le fonctionnement du dispositif de condamnation (s'il existe)"),
        ("Verifier l'impossibilite de fonctionnement simultane de la telecommande et du poste de conduite principal", "Ne procede pas a l'essai depuis le poste de conduite principal, apres avoir mis en service la telecommande"),
        ("Enumerer les risques lies a l'utilisation de la telecommande", "N'est pas capable de citer au moins quatre risques"),
        ("Savoir se positionner par rapport a la zone de travail et d'evolution de l'engin", "Lors des essais de fonctionnement, ne se tient pas de facon a voir le resultat des essais, tout en etant suffisamment eloigne des parties mobiles de l'engin"),
        ("Verifier au prealable l'environnement de travail", "N'identifie pas au prealable les points de vigilance du parcours"),
        ("Se positionner pour avoir la meilleure vision de la manoeuvre et de son environnement, tout en restant hors de la zone de risque", "Ne conserve pas une vision degagee de l'engin et de la zone, en permanence / Se tient dans la zone immediate de manoeuvre de l'engin, ou dans le rayon d'action des equipements"),
        ("Garantir la securite des pietons", "Ne prend pas en compte un pieton dans ou a proximite de sa zone de travail (different de la faute eliminatoire, qui est le danger reel occasionne par un pieton proche de l'engin)"),
        ("Effectuer les manoeuvres avec souplesse et precision", "Donne des a-coups injustifies / Ne parvient pas a adapter ses trajectoires / Heurte un obstacle / Roule en dehors du chemin (talus, fosse…)"),
        ("Au moyen de la telecommande, realiser les travaux pour lesquels l'engin est concu", "Se referer aux criteres definis dans la grille d'evaluation de la categorie (PE 4, 5, 6 et 7)"),
    ],
}

def grilles_du_bloc(bloc):
    if bloc == "base":
        return db.query(GrillePratique).filter(
            GrillePratique.recommandation == "R.482",
            GrillePratique.categorie == "F",
            GrillePratique.type == "base").all()
    return db.query(GrillePratique).filter(
        GrillePratique.recommandation == "R.482",
        GrillePratique.categorie == "F",
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
                print("[MISS %s] %s" % (bloc, it.libelle[:50]))
    db.commit()

print("[OK] %d criteres ecrits, %d lignes notees sans critere" % (total_ok, total_miss))
db.close()
