"""Patch idempotent : remplit ItemPratique.critere_evaluation (colonne L Excel)
sur la grille R.486 C (base, PE integre). Matching par libelle normalise. Relancable."""
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
    t = str(t).lower().replace("’", "'").replace("…", "...").strip()
    if t.startswith("* "): t = t[2:]
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    while "  " in t: t = t.replace("  ", " ")
    return t

CRITERES = {
    "Notice d'instructions (justifier une interdiction d'emploi ou une règle d'utilisation)": "Ne donne pas une justification correcte",
    "Rapport de vérification générale périodique, de mise ou de remise en service (vérifier l'absence d'observation ou de restriction d'usage)": "Ne comprend pas le rapport / Ne vérifie pas la date du rapport / Ne vérifie pas la conclusion",
    "Procéder à une vérification visuelle de la PEMP": "Ne vérifie pas l'ensemble élévateur (vérins, flexibles, axes)",
    "Vérifier le bon fonctionnement des mécanismes et des dispositifs de sécurité accessibles": "Ne vérifie pas deux de ces points : coupe-circuit, commandes du poste bas et haut, arrêt d'urgence",
    "Identifier les risques liés à la zone d'évolution": "Ne prend pas en compte l'environnement avant de travailler",
    "Baliser la zone d'intervention": "Ne pose aucun balisage",
    "Déployer les stabilisateurs": "N'utilise pas les plaques de calage sur un sol meuble / Un stabilisateur au moins n'est pas déployé",
    "Régler l'horizontalité de la PEMP": "L'indicateur est en dehors de la limite permise",
    "Replier les stabilisateurs": "Un stabilisateur au moins n'est pas complètement rentré",
    "Adapter sa conduite aux conditions de circulation (évalué en continu)": "Heurte un objet / Effectue plus de 2 translations inutiles / Conduit de manière dangereuse",
    "Effectuer les manoeuvres avec souplesse et précision (évalué en continu)": "Donne des à-coups injustifiés",
    "Regarder en arrière avant de reculer (évalué en continu)": "Ne regarde pas avant la manœuvre, dans une situation qui le justifie",
    "Utiliser correctement l'avertisseur sonore (évalué en continu)": "N'utilise pas l'avertisseur sonore dans une situation de danger",
    "Respecter les règles et panneaux de circulation (évalué en continu)": "Ne respecte pas une obligation ou interdiction",
    "Comprendre / exécuter les gestes de commandement (évalué en continu)": "Ne comprend pas toute la gestuelle du testeur avant ou pendant le travail",
    "Savoir réagir à un signal d'alerte (évalué en continu)": "N'est pas capable de dire ce qu'il faut faire en cas de signal d'alerte",
    "Positionner la PEMP à un emplacement précis (aire limitée au sol)": "Heurte un objet / Effectue plus de 2 translations inutiles",
    "Circuler plate-forme en position basse orientée dans le sens de la marche, en marche avant / arrière, en ligne droite / en virages": "Heurte un objet / Effectue plus de 2 translations inutiles / Se trompe de commande",
    "Circuler plate-forme en position basse orientée dans le sens inverse de la marche, en marche avant / arrière, en ligne droite / en virages": "Heurte un objet / Effectue plus de 2 translations inutiles / Se trompe de commande",
    "Effectuer les manoeuvres de secours (au moyen des commandes de secours et de dépannage)": "Ne peut pas expliquer en totalité chacune des deux manœuvres",
    "S'assurer de l'adéquation de la PEMP et du porte-engins": "Ne détermine pas la capacité exacte du porte-engins",
    "Vérifier que les conditions permettant le chargement / déchargement sont remplies": "Ne vérifie pas le calage du porte-engins / Ne vérifie pas l'état du plancher",
    "Monter la PEMP sur le porte-engins dans le sens approprié": "Ne monte pas dans le sens indiqué par le fabricant / Ne parvient pas à monter en sécurité",
    "Positionner la PEMP sur le porte-engins pour assurer l'équilibre et la stabilité": "Le chargement n'est pas équilibré par rapport à l'axe longitudinal et transversal",
    "Mettre la PEMP en configuration de transport et la stabiliser": "Ne coupe pas les énergies / La PEMP peut glisser et se déplacer",
    "Identifier et désigner les points d'arrimage sur le porte-engins et sur la PEMP": "Les points désignés ne permettent pas l'arrimage selon les préconisations",
    "Trouver le mode d'arrimage approprié (notice d'instructions…)": "Ne trouve pas le mode d'arrimage dans la notice (s'il existe) ou ne propose pas de solution",
    "S'assurer de l'adéquation des moyens d'arrimage proposés": "Les moyens choisis ne sont pas adéquats",
    "S'assurer que l'environnement du porte-engins permet le déchargement": "Ne vérifie pas l'absence de coactivité",
    "Positionner la PEMP pour la descente et la descendre en sécurité": "Ne parvient pas à adapter ses trajectoires / Perd le contrôle lors de la descente",
    "Mettre la PEMP en position hors-service": "Ne vérifie pas le niveau restant d'énergie / Ne retire pas la clé ou ne condamne pas les commandes",
    "Réaliser des opérations de maintenance journalière": "N'est pas capable d'expliquer les modalités de vérification et de mise à niveau",
    "Rendre compte des anomalies relevées": "Ne cite pas le carnet d'entretien comme moyen de signaler les anomalies",
}

CRIT_NORM = {norm(k): v for k, v in CRITERES.items()}

grilles = db.query(GrillePratique).filter(
    GrillePratique.recommandation == "R.486",
    GrillePratique.categorie == "C",
).all()
nb_ok = 0; nb_miss = 0; manquants = []
for g in grilles:
    for th in g.themes:
        for pe in th.points:
            for it in pe.items:
                if it.descriptif_seul: continue
                key = norm(it.libelle)
                if key in CRIT_NORM:
                    it.critere_evaluation = CRIT_NORM[key]; nb_ok += 1
                else:
                    nb_miss += 1; manquants.append(it.libelle[:60])
db.commit()
print("[OK] R.486 C : %s criteres ecrits, %s manquants" % (nb_ok, nb_miss))
for m in manquants: print("   MANQUANT:", m)
