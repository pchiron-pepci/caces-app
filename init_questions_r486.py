"""
init_questions_r486.py
Reinitialise les grilles et questions theoriques R.486 (PEMP).
5 grilles x 100 questions. Structure : 4 themes (14 / 26 / 54 / 6 = 100 pts).
Textes lus sur les fiches INRS V1 - 12/2024 ; reponses issues du corrige officiel.
Convention images/audio : R486_G{grille}_T{theme}_Q{numero} (underscores, matching upload.py).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille

# Structure : {grille_numero: {theme: [(numero_question, texte, reponse_correcte)]}}
GRILLES_R486 = {

    1: {
        1: [
            (1, "Le constructeur est responsable du marquage CE de la PEMP", True),
            (2, "L'employeur est responsable du maintien en état de la PEMP", True),
            (3, "Le chef de chantier peut imposer au conducteur d'effectuer une manœuvre dangereuse", False),
            (4, "Le marquage CE atteste du bon état de la PEMP", False),
            (5, "Lors de la prise de poste, le conducteur doit vérifier que la PEMP est en bon état", True),
            (6, "Le conducteur peut manœuvrer la PEMP lorsqu'il est seul sur le chantier", False),
            (7, "Le conducteur de la PEMP doit effectuer toutes les manœuvres demandées par son responsable", False),
            (8, "Lorsque l'opérateur dans la plateforme de travail n'est pas formé, l'accompagnateur peut manœuvrer la PEMP depuis le sol au moyen du poste de secours", False),
            (9, "La détention d'un CACES® R.486 suffit pour permettre au conducteur d'effectuer les VGP réglementaires des PEMP", False),
            (10, "Le contrôleur de la [Carsat/Cramif/CGSS] délivre les autorisations de conduite", False),
            (11, "L'inspecteur du travail peut arrêter un chantier en cas de danger grave et imminent", True),
            (12, "Cette PEMP (rouge) appartient à la catégorie B de la recommandation CACES® R.486", False),
            (13, "Cette PEMP (bleue) appartient à la catégorie A de la recommandation CACES® R.486", True),
            (14, "Le CACES® R.486 de catégorie C permet de délivrer une autorisation de conduite \"hors production\" pour cette PEMP", True),
        ],
        2: [
            (1, "[1] est le bras pendulaire", True),
            (2, "[2] est le châssis de la PEMP", False),
            (3, "La CMU est l'une des caractéristiques générales d'une PEMP", True),
            (4, "Le dévers maximum admissible est l'une des caractéristiques générales d'une PEMP", True),
            (5, "Lorsque la plate-forme est en position haute, la PEMP peut se déplacer à sa vitesse maximale", False),
            (6, "Les mouvements de levage sont réalisés par la circulation d'huile dans des vérins", True),
            (7, "Le poste de commande de secours est toujours prioritaire par rapport au poste de commande situé dans la plate-forme", True),
            (8, "Sur les PEMP de catégorie 3B, le poste de commande principal est le poste situé au niveau du sol", False),
            (9, "Les commandes des mouvements de levage doivent être à action maintenue", True),
            (10, "La molette [1] permet le réglage de la vitesse maximale des mouvements", True),
            (11, "Lorsque la plate-forme est en élévation, le déclenchement du limiteur de dévers interrompt le mouvement de translation", True),
            (12, "Une PEMP est équipée d'un bouton d'arrêt d'urgence au poste de commande", True),
            (13, "Le limiteur de charge permet d'éviter tout contact de la PEMP avec des obstacles", False),
            (14, "La batterie d'une PEMP électrique peut être remplacée par une batterie de masse inférieure", False),
            (15, "La position du centre de gravité d'une PEMP ne varie pas lors de l'élévation de la plate-forme", False),
            (16, "La masse de la PEMP est indiquée sur la plaque constructeur", True),
            (17, "Si M1 = 2 x M2 et L2 = 2 x L1, la balance reste en équilibre", True),
            (18, "Si M2 = 0,5 x M1 et L1 = 2 x L2, la balance reste en équilibre", False),
            (19, "Le télescopage de la plate-forme à l'extérieur du polygone de sustentation réduit la stabilité de la PEMP", True),
            (20, "L'élévation de la plate-forme d'une PEMP du groupe A améliore sa stabilité", False),
            (21, "Il est possible de travailler à une hauteur de 13 m avec un déport de 8 m", False),
            (22, "Il est possible de travailler à une hauteur de 13 m avec un déport de 3 m", True),
            (23, "Il est possible de travailler à une hauteur de 4 m avec un déport de 5 m", True),
            (24, "Le conducteur peut embarquer une charge de 150 kg dans la plate-forme", False),
            (25, "Pour positionner les stabilisateurs d'une PEMP sur un terrain meuble, le conducteur doit utiliser des plaques de répartition adaptées", True),
            (26, "Les stabilisateurs d'une PEMP peuvent être calés au moyen de parpaings creux", False),
        ],
        3: [
            (1, "La mise en place d'une PEMP sur un sol non stabilisé peut causer son renversement", True),
            (2, "La rupture d'un flexible hydraulique ne peut pas causer le renversement de la PEMP", False),
            (3, "La surcharge de la plate-forme d'une PEMP peut causer son renversement", True),
            (4, "Il est autorisé de monter sur la plinthe de la plate-forme pour atteindre un endroit inaccessible", False),
            (5, "L'utilisateur peut souder un point d'ancrage supplémentaire dans la plate-forme sans consulter le constructeur de la PEMP", False),
            (6, "Dans une PEMP, le port du harnais permet d'éviter l'éjection depuis la plate-forme", True),
            (7, "Lors du déploiement de la PEMP, le conducteur doit s'assurer qu'aucun obstacle n'entrave les mouvements de la structure", True),
            (8, "Pendant l'utilisation de la PEMP, l'accompagnateur peut rester dans la zone d'évolution balisée", False),
            (9, "Avant de commander un mouvement de la PEMP, le conducteur doit regarder dans le sens du déplacement", True),
            (10, "Avec une PEMP de CMU 200 kg / 2 personnes, il est autorisé d'élever 3 personnes de 65 kg chacune dans la plate-forme", False),
            (11, "Il est permis d'effectuer le levage d'une charge suspendue sous la plate-forme d'une PEMP", False),
            (12, "Il est interdit de remplacer une ampoule électrique au moyen d'une PEMP", False),
            (13, "La zone de travail doit être balisée avant l'utilisation de la PEMP", True),
            (14, "Le conducteur d'une PEMP peut survoler temporairement avec la plate-forme une zone où travaillent des salariés", False),
            (15, "Le conducteur est responsable du balisage de la zone de travail", True),
            (16, "La consignation d'un pont roulant situé dans la zone d'évolution de la PEMP permet de limiter les risques de collision entre les deux équipements", True),
            (17, "Lors du travail en coactivité d'une PEMP et d'une grue mobile, des mesures organisationnelles doivent être mises en place pour limiter les risques de collision", True),
            (18, "Sur la voie publique, il n'est pas nécessaire de baliser la zone de travail d'une PEMP", False),
            (19, "La distance minimale à respecter entre une ligne électrique nue sous une tension de 60000 V et le point conducteur le plus proche d'une PEMP est de 6 m", False),
            (20, "La distance minimale à respecter entre une ligne électrique nue sous une tension de 25 kV et le point conducteur le plus proche d'une grue de chargement est de 3 m", False),
            (21, "Le conducteur peut stationner la PEMP au bord d'une fouille", False),
            (22, "Le conducteur de la PEMP peut réaliser une manœuvre depuis la plate-forme sans aucune visibilité sur le sol", False),
            (23, "L'élévation de la plateforme peut permettre d'améliorer la visibilité lors de la translation de la PEMP", True),
            (24, "Dans l'obscurité, le conducteur est autorisé à se faire guider par l'accompagnateur au sol", False),
            (25, "Lors de l'utilisation d'un poste à souder dans une PEMP, un extincteur doit être disponible dans la plate-forme", True),
            (26, "Les bouteilles de gaz doivent être éloignées de la zone de soudure", True),
            (27, "Le tirage de câbles électriques par un opérateur situé dans la plate-forme ne présente aucun risque", False),
            (28, "Le conducteur de PEMP ne doit pas commencer un chantier lorsque la météo prévoit des rafales de vent à plus de 45 km/h toute la journée", False),
            (29, "Par temps orageux, le conducteur dans la plate-forme n'est pas exposé et peut travailler sans risques", False),
            (30, "Avec une PEMP, il est autorisé de circuler sur un sol verglacé", False),
            (31, "Le poste de secours peut être utilisé en cas de malaise du conducteur sur la plate-forme", True),
            (32, "Depuis le poste de dépannage, il est possible de commander la translation de la PEMP", False),
            (33, "Une PEMP est toujours prioritaire par rapport aux autres engins mobiles", False),
            (34, "L'utilisation de plusieurs PEMP dans la même zone d'intervention ne présente pas de risques", False),
            (35, "Une PEMP à moteur thermique peut manœuvrer temporairement dans un local clos", False),
            (36, "Les gaz d'échappement d'une PEMP à moteur thermique peuvent causer un malaise du conducteur", True),
            (37, "La recherche d'une fuite hydraulique nécessite le port de gants et de lunettes de protection adaptés", True),
            (38, "Le local de charge des batteries d'une PEMP électrique doit être ventilé", True),
            (39, "Pendant le plein de carburant, le conducteur doit éteindre son téléphone mobile", True),
            (40, "Le conducteur peut fumer une cigarette en effectuant le plein de carburant", False),
            (41, "La prise de médicament n'influe jamais sur la capacité à conduire une PEMP", False),
            (42, "L'utilisation d'un téléphone mobile pendant la conduite d'une PEMP ne crée pas de risque", False),
            (43, "La vitesse maximale de vent autorisée lors de l'utilisation d'une PEMP conçue pour travailler à l'extérieur est de 45 km/h", True),
            (44, "Une PEMP équipée de bandages est conçue pour circuler en tout-terrain sur un chantier", False),
            (45, "Une PEMP dont la pente maximale autorisée est de 3° peut circuler sur une rampe de longueur 10 m et de dénivelé 1 m", False),
            (46, "Lorsque la notice d'instructions de la PEMP ne précise rien à ce sujet, le conducteur peut raccorder les EPI contre les chutes là où il le souhaite", False),
            (47, "Les EPI contre les chutes de hauteur doivent comporter un marquage CE", True),
            (48, "Le balisage doit délimiter la totalité de la zone de travail", True),
            (49, "Le balisage doit aussi être réalisé en hauteur", False),
            (50, "Lorsque la zone d'évolution de la PEMP est balisée, il n'est pas nécessaire de prévoir la présence d'un accompagnateur au sol", False),
            (51, "Ce panneau signifie \"Danger, chaussée rétrécie\"", True),
            (52, "Ce panneau indique une interdiction de circuler", False),
            (53, "Le bouton [1] commande l'avertisseur sonore", True),
            (54, "Le pictogramme [2] concerne le mouvement de translation de la PEMP", False),
        ],
        4: [
            (1, "Le conducteur doit signaler un niveau d'huile hydraulique insuffisant", True),
            (2, "Le conducteur peut procéder lui-même au remplacement d'un flexible hydraulique endommagé", False),
            (3, "Sur une PEMP, un vérin de stabilisateur dont la tige rentre sous charge ne crée pas de risques", False),
            (4, "Une PEMP dont le châssis est fissuré doit être immédiatement consignée et signalée à un responsable", True),
            (5, "Si un élément de structure de la PEMP est déformé, le conducteur doit le redresser lui-même et le plus rapidement possible", False),
            (6, "Lorsque le rapport mentionne qu'un élément de charpente était fissuré lors de la dernière VGP (vérification générale périodique), le conducteur doit s'assurer que les réparations ont été réalisées avant d'utiliser la PEMP", True),
        ],
    },

    # Grilles 2 a 5 : a completer (transcription en cours)
}

POINTS_THEME = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}


def get_image_url(grille: int, theme: int, question: int) -> str:
    # Convention underscore (matching upload.py : filename.split("_"))
    return f"R486_G{grille}_T{theme}_Q{question}"


def main():
    db = SessionLocal()
    try:
        print("=== Reinitialisation grilles R486 ===\n")

        nb_util = db.query(UtilisationGrille).join(GrilleTheorie).filter(
            GrilleTheorie.famille == "R486"
        ).count()
        if nb_util > 0:
            print(f"ATTENTION : {nb_util} utilisation(s) de grille R486 seront supprimees.")

        grilles_existantes = db.query(GrilleTheorie).filter(
            GrilleTheorie.famille == "R486"
        ).all()
        for g in grilles_existantes:
            db.query(UtilisationGrille).filter(UtilisationGrille.grille_id == g.id).delete()
            db.query(ReponseGrille).filter(ReponseGrille.grille_id == g.id).delete()
            db.delete(g)
        db.commit()
        print(f"OK : {len(grilles_existantes)} grille(s) existante(s) supprimee(s)\n")

        total_questions = 0
        for grille_num, themes in GRILLES_R486.items():
            grille = GrilleTheorie(
                famille="R486",
                numero=grille_num,
                annee=2024,
                actif=True
            )
            db.add(grille)
            db.flush()

            nb_q = 0
            for theme_num, questions in themes.items():
                for (q_num, texte, reponse) in questions:
                    rg = ReponseGrille(
                        grille_id=grille.id,
                        theme=theme_num,
                        numero_question=q_num,
                        reponse_correcte=reponse,
                        points=POINTS_THEME[theme_num],
                        texte_question=texte,
                        image_url=get_image_url(grille_num, theme_num, q_num)
                    )
                    db.add(rg)
                    nb_q += 1

            db.commit()
            total_questions += nb_q
            print(f"OK Grille {grille_num} - {nb_q} questions creees (id={grille.id})")

        print(f"\nOK Total : {total_questions} questions pour {len(GRILLES_R486)} grille(s) R486\n")

        print("Verification :")
        for grille_num in GRILLES_R486:
            g = db.query(GrilleTheorie).filter(
                GrilleTheorie.famille == "R486",
                GrilleTheorie.numero == grille_num
            ).first()
            counts = {}
            for t in range(1, 5):
                c = db.query(ReponseGrille).filter(
                    ReponseGrille.grille_id == g.id,
                    ReponseGrille.theme == t
                ).count()
                counts[t] = c
            tot = sum(counts.values())
            print(f"  Grille {grille_num} : T1={counts[1]} T2={counts[2]} T3={counts[3]} T4={counts[4]} => {tot}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
