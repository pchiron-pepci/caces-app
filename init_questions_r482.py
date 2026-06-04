"""
init_questions_r482.py
Réinitialise complètement les grilles et questions R482 (5 grilles × 100 questions).
Textes extraits des PDFs INRS V1 - 12/2024.
Convention images : R482-G{grille}-T{theme}-Q{numero}.png (ou .jpg)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille, UtilisationGrille

# ─── Données complètes ────────────────────────────────────────────────────────
# Structure : {grille_numero: {theme: [(numero_question, texte, reponse_correcte)]}}

GRILLES_R482 = {

    1: {
        1: [
            (1,  "Le constructeur est responsable du maintien en état de conformité de l'engin", False),
            (2,  "L'employeur doit réaliser les VGP (vérifications générales périodiques)", False),
            (3,  "L'autorisation de conduite est délivrée par le constructeur de l'engin", False),
            (4,  "Le conducteur doit s'assurer que l'engin est en bon état lors de la prise de poste", True),
            (5,  "Le conducteur peut utiliser un engin sans autorisation de conduite", False),
            (6,  "Pour conduire un engin de chantier, il faut obligatoirement le permis B", False),
            (7,  "Le signaleur doit posséder une autorisation de conduite", False),
            (8,  "Le chef de chantier doit veiller à la sécurité de ses équipes", True),
            (9,  "L'inspecteur du travail veille au respect du droit du travail", True),
            (10, "Les contrôleurs de la [Carsat/Cramif/CGSS] peuvent infliger des amendes administratives", False),
            (11, "Une pelle hydraulique de masse supérieure à 6000 kg appartient à la catégorie B1 de la recommandation CACES® R.482", True),
            (12, "Une petite niveleuse appartient à la catégorie A de la recommandation CACES® R.482", False),
        ],
        2: [
            (1,  "[1] est le balancier", True),
            (2,  "Cette niveleuse est équipée d'un scarificateur", True),
            (3,  "La foreuse est un engin à déplacement alternatif", False),
            (4,  "La masse en service de l'engin est indiquée sur la plaque constructeur", True),
            (5,  "Un moteur utilisé sans filtre à air s'use prématurément", True),
            (6,  "Ce vérin situé sur le balancier de la pelle permet le mouvement du godet", True),
            (7,  "Le circuit de refroidissement moteur sert à maintenir le moteur à une température adéquate", True),
            (8,  "Sur une chargeuse pelleteuse, le différentiel permet de rouler plus vite", False),
            (9,  "Sur le schéma hydraulique suivant, si a=1 et b=0, alors la tige du vérin rentre", False),
            (10, "Dans cette chaîne cinématique de chargeuse, [B] est le moteur thermique", False),
            (11, "Cet équipement est une attache rapide mécanique", True),
            (12, "L'utilisation d'équipements interchangeables ne nécessite pas de formation particulière", False),
            (13, "Sur cette pelle hydraulique, le levier de commande [5] est un levier de translation", True),
            (14, "Le relevage de la poignée rouge désactive les commandes hydrauliques", True),
            (15, "Sur un crochet de levage, le linguet est facultatif", False),
            (16, "L'électromodule de surveillance permet la gestion du fonctionnement du moteur, des circuits électrique et hydrostatique", True),
            (17, "Une cabine ROPS protège le conducteur en cas de retournement de l'engin", True),
            (18, "Le terme FOPS signifie que la cabine de l'engin est climatisée", False),
            (19, "Lors de l'utilisation d'un engin de chantier équipé d'une cabine ROPS, le port de la ceinture de sécurité est laissé à l'appréciation du chef d'établissement", False),
            (20, "La ceinture de sécurité doit toujours être utilisée", True),
            (21, "Le conducteur doit régler ou vérifier le réglage du siège de l'engin à la prise de poste", True),
            (22, "Les vibrations mécaniques produites par les engins ne sont pas transmises au conducteur", False),
            (23, "Ce voyant concerne la pression de gonflage des pneumatiques", False),
            (24, "Ce voyant est un indicateur de colmatage du filtre à air", True),
            (25, "La stabilité de l'engin dépend de la position de son centre de gravité", True),
            (26, "Un engin ne peut pas se renverser latéralement", False),
            (27, "Freiner brusquement ne présente pas de risques de renversement", False),
            (28, "Pour éviter de « cabrer » lors de la montée d'une pente importante, le poids de l'engin doit être situé vers le haut de la rampe", True),
        ],
        3: [
            (1,  "Avant de procéder à une marche arrière, il est impératif de regarder vers l'arrière ainsi que dans les rétroviseurs", True),
            (2,  "Un angle mort est une zone qui n'est pas vue depuis le poste de conduite", True),
            (3,  "Le signal sonore de marche arrière supprime totalement le risque de heurt entre l'engin et une personne", False),
            (4,  "Lorsque le personnel à pied est interdit sur le chantier, le conducteur peut effectuer les manœuvres sans précautions particulières", False),
            (5,  "Lors de la manutention d'une charge sans visibilité, le conducteur doit être guidé par une personne formée", True),
            (6,  "Toutes les vitres de l'engin et tous les rétroviseurs doivent être propres et en bon état", True),
            (7,  "Lorsqu'il guide un déplacement en marche arrière sans visibilité, le chef de manœuvre doit se tenir juste derrière l'engin", False),
            (8,  "Avec un engin compact, le conducteur peut effectuer une marche arrière sans visibilité à faible vitesse", False),
            (9,  "Sur une courte distance, le conducteur peut transporter une personne debout dans la cabine de l'engin", False),
            (10, "Le transport de personnel est autorisé si l'engin est équipé d'un second siège avec ceinture", True),
            (11, "Si l'engin possède de larges marchepieds antidérapants, il est autorisé d'y transporter du personnel", False),
            (12, "Il est interdit de lever des personnes avec un engin non conçu à cet effet", True),
            (13, "Il est autorisé de lever une personne dans le godet d'un engin, avec l'accord du chef d'établissement", False),
            (14, "L'élévation de personne est autorisée avec un engin dont les VGP sont à jour et sans réserve", False),
            (15, "Le conducteur doit réduire sa vitesse avant d'aborder une descente", True),
            (16, "En cas de perte de contrôle de l'engin, le conducteur doit sauter par la porte le plus vite possible", False),
            (17, "Dans une descente, pour éviter la perte de contrôle de l'engin, le conducteur doit mettre la boite de vitesses au point mort", False),
            (18, "Les parties tournantes du moteur (ventilateurs et courroies) présentent des risques", True),
            (19, "Sur une foreuse, il ne faut jamais intervenir sur un train de tiges avant l'arrêt complet de la rotation", True),
            (20, "Occasionnellement, le graissage des cardans peut se faire moteur tournant", False),
            (21, "Le démontage d'un flexible hydraulique peut être effectué sans précautions particulières", False),
            (22, "En cas d'intervention sur le circuit électrique, il faut couper l'alimentation électrique avec le coupe-circuit", True),
            (23, "Il est autorisé d'agir sur les commandes d'un engin depuis le sol", False),
            (24, "Sur une pelle, le levier de sécurité désactive les commandes de l'équipement", True),
            (25, "Pour gonfler un pneu d'engin, il faut se positionner face à la roue pour bien surveiller le gonflage", False),
            (26, "Le contrôle de la pression des pneumatiques doit toujours se faire à froid", True),
            (27, "Le passage en bord de fouille avec un engin ne présente pas de danger particulier", False),
            (28, "La distance à respecter par rapport à une fouille ou un talus dépend des conditions météorologiques", True),
            (29, "La position correcte du crochet est celle de gauche", True),
            (30, "Un câble de levage qui présente une rupture mineure doit être immédiatement remplacé", True),
            (31, "A défaut de rampes d'accès, il est autorisé d'utiliser des planches pour le chargement d'une mini pelle sur un porte-engin", False),
            (32, "Il est interdit de procéder au chargement ou au déchargement d'un engin sur un porte-engins positionné en dévers", True),
            (33, "Un grillage avertisseur de couleur rouge signale une canalisation d'eaux usées", False),
            (34, "Lors de travaux à proximité d'une ligne électrique aérienne, le risque d'amorçage de l'arc électrique est le même pour les engins à chenilles ou sur pneumatiques", True),
            (35, "La consommation de produits stupéfiants ne crée pas de risques lorsqu'elle est occasionnelle", False),
            (36, "La consommation d'alcool augmente le risque d'accident", True),
            (37, "Même en phase de conduite, le conducteur doit immédiatement répondre au téléphone lorsque son responsable l'appelle", False),
            (38, "Écouter de la musique avec un casque réduit la vigilance du conducteur", True),
            (39, "L'utilisation d'un engin à moteur Diesel à l'intérieur d'un bâtiment ne crée aucun risque pour les salariés", False),
            (40, "Il est impératif de couper le moteur de l'engin lors du ravitaillement en carburant", True),
            (41, "Lorsqu'il est vide, un bidon qui a contenu de l'AdBlue® peut être réutilisé pour transporter de l'eau potable", False),
            (42, "Lors de manipulation de produits hydrocarbures, l'opérateur doit porter des gants de protection", True),
            (43, "La vitesse de conduite n'a pas d'influence sur le niveau des vibrations transmises au conducteur", False),
            (44, "Le volume sonore à partir duquel il est obligatoire de se protéger est de 85 db(A)", True),
        ],
        4: [
            (1,  "Sur un chantier, un panneau rond à fond bleu indique un danger", False),
            (2,  "Ce panneau indique un rétrécissement de la chaussée", True),
            (3,  "Le signaleur ordonne un arrêt d'urgence", True),
            (4,  "Ce geste signifie « lever la benne »", False),
            (5,  "La distance d'arrêt d'un engin est plus importante lorsqu'il est à vide qu'en charge", False),
            (6,  "Lorsqu'il circule en descente avec un tombereau en charge, le conducteur doit sélectionner le rapport de boite qui procure le meilleur frein moteur", True),
            (7,  "La distance de sécurité à conserver entre deux engins en circulation dépend de la charge transportée", False),
            (8,  "Pour réduire les risques de collision, il est impératif de conserver une distance de sécurité appropriée entre deux engins en circulation", True),
            (9,  "Lorsque la piste est dégagée, il est permis de faire la course entre tombereaux pour augmenter la production du chantier", False),
            (10, "Les règles de dépassement doivent être indiquées dans le plan de circulation du chantier", True),
            (11, "La présence d'un gyrophare suffit pour être autorisé à se déplacer sur la route avec un engin", False),
            (12, "La vitesse de déplacement autorisée pour un engin sur la route est de 25 km/h maximum", False),
        ],
        5: [
            (1,  "En début de poste, le conducteur doit s'assurer du bon fonctionnement des freins de l'engin", True),
            (2,  "En fin de poste la cabine doit être nettoyée et laissée propre", True),
            (3,  "Lorsqu'il constate que la date de validité de la VGP de l'engin est dépassée, le conducteur doit en informer son responsable", True),
            (4,  "Tout incident ou défaillance doit être signalé selon la procédure en vigueur dans l'entreprise", True),
        ],
    },

    2: {
        1: [
            (1,  "La vérification de l'adéquation du matériel au travail à réaliser est de la responsabilité du fabricant de l'engin", False),
            (2,  "Le chef d'établissement doit délivrer une autorisation de conduite à son salarié conducteur d'engin", True),
            (3,  "Le fabricant doit s'assurer que les conducteurs ont reçu une formation adaptée à la conduite", False),
            (4,  "Le conducteur signale à son responsable les situations dangereuses rencontrées et les consigne dans le registre d'observations", True),
            (5,  "Un salarié peut utiliser un engin sans avoir reçu de formation", False),
            (6,  "Le conducteur d'engin est responsable de la réalisation de vérification lors de la prise de poste", True),
            (7,  "Le chef de chantier peut conduire tous les engins sur le chantier sans autorisation de conduite", False),
            (8,  "Le signaleur a pour mission principale de garer les engins en fin de poste", False),
            (9,  "La [Carsat/Cramif/CGSS] a pour mission de veiller à la prévention des accidents du travail et des maladies professionnelles", True),
            (10, "L'OPPBTP est une caisse de congés payés du bâtiment", False),
            (11, "Une chargeuse-pelleteuse de masse 8 tonnes est un engin compact, au sens de la recommandation CACES® R.482", False),
            (12, "Une pelle rail-route n'appartient pas à la catégorie A de la recommandation CACES® R.482", True),
        ],
        2: [
            (1,  "Cet élément est la couronne d'orientation de la tourelle", True),
            (2,  "Cet élément d'une chargeuse-pelleteuse est le godet rétro", True),
            (3,  "La capacité d'un godet est exprimée en tonnes", False),
            (4,  "Les informations concernant le gabarit de l'engin sont disponibles dans le manuel d'utilisation", True),
            (5,  "Sur les chenilles d'un bouteur, les barbotins sont à l'arrière", False),
            (6,  "Sur un engin, le pont est l'ensemble des organes qui assurent la transmission du mouvement depuis le moteur jusqu'aux roues", True),
            (7,  "Le système de freinage des engins de chantier est hydraulique", False),
            (8,  "Sur le schéma hydraulique suivant, si a=1 et b=0, alors la tige du vérin reste fixe", False),
            (9,  "Cet élément de la chaîne cinématique du tombereau est l'arbre de transmission", True),
            (10, "Le système de freinage des tombereaux est refroidi à l'eau", True),
            (11, "Cet équipement est un brise-roche", True),
            (12, "Il n'est pas nécessaire que les équipements interchangeables installés sur les foreuses soient adaptés à l'engin", False),
            (13, "Sur une pelle, la manœuvre du manipulateur gauche [3] permet de tourner à gauche", False),
            (14, "Lors de la mise en route de l'engin, tous les leviers doivent être en position neutre", True),
            (15, "Un avertisseur sonore de recul doit être présent sur tous les engins de chantier", True),
            (16, "Les vérins de flèche doivent être équipés de clapets de sécurité", True),
            (17, "Une cabine TOPS protège l'opérateur en cas de retournement", False),
            (18, "Une cabine FOPS est une cabine qui protège contre les chutes d'objets", True),
            (19, "Lorsque le conducteur monte et descend régulièrement de l'engin, le port de la ceinture est facultatif", False),
            (20, "Ce pictogramme impose l'utilisation de la ceinture de sécurité", True),
            (21, "Un siège correctement réglé permet de réduire le risque de douleurs lombaires", True),
            (22, "Le conducteur n'a pas besoin de régler le siège d'un engin de nivellement", False),
            (23, "Le conducteur n'a pas besoin de connaître tous les symboles des avertisseurs (sonores, lumineux...) du tableau de bord de son engin", False),
            (24, "Ce voyant alerte d'un défaut sur le filtre à particules", True),
            (25, "Une vitesse excessive en virage peut causer le renversement d'un engin de chantier", True),
            (26, "Un engin dont les pneumatiques sont correctement gonflés ne peut pas se renverser latéralement", False),
            (27, "Sur un terrain plat, le conducteur d'un tombereau rigide peut circuler benne levée", False),
            (28, "Pour descendre une forte pente avec une charge importante sur les bras de fourche, le conducteur doit circuler en marche arrière", True),
        ],
        3: [
            (1,  "La limitation de la vitesse des engins sur chantier permet de réduire les risques de heurts", True),
            (2,  "Lors de la mise en route de l'engin, le conducteur doit vérifier que l'avertisseur de recul fonctionne", True),
            (3,  "Sur un engin de chantier, le seul moyen permettant de limiter les risques de heurt de piétons est l'installation de caméras de recul", False),
            (4,  "Lorsque l'engin est équipé d'une caméra de recul, le réglage des rétroviseurs n'est pas nécessaire", False),
            (5,  "Lorsqu'il guide un déplacement en marche arrière sans visibilité, le chef de manœuvre doit se tenir dans le champ de vision du conducteur", True),
            (6,  "Pour déposer une charge derrière une banche, le conducteur doit se faire aider par un chef de manœuvre", True),
            (7,  "Sur un chantier dans le brouillard, le gyrophare est obligatoire", False),
            (8,  "Lors d'un déplacement sur route, l'engin doit être équipé de caméras", False),
            (9,  "Le transport d'une personne n'est permis que s'il y a un second siège prévu par le constructeur", True),
            (10, "Le transport de personnel dans le godet est interdit", True),
            (11, "Le transport de personnel est autorisé si le passager est installé sur le contrepoids et qu'il est attaché avec un harnais", False),
            (12, "Il est strictement interdit de monter dans un godet pour effectuer un travail en hauteur", True),
            (13, "L'élévation de personnel avec une chargeuse est autorisée si la personne est équipée d'un harnais", False),
            (14, "Lorsque l'engin est équipé de clapets anti-retour, l'élévation de personnel dans le godet est autorisée", False),
            (15, "En cas de perte de contrôle de l'engin en descente, le conducteur peut utiliser le frein de secours", True),
            (16, "En cas de perte de contrôle de l'engin, le conducteur doit immédiatement téléphoner au chef de chantier", False),
            (17, "Pour économiser du carburant, il est recommandé de circuler au point mort dans les descentes", False),
            (18, "Les vêtements larges et flottants sont proscrits", True),
            (19, "Lors des opérations d'entretien, il faut obligatoirement consigner l'engin afin d'éviter une mise en route intempestive", True),
            (20, "Le conducteur peut intervenir sur les parties tournantes du moteur d'une niveleuse non arrêtée", False),
            (21, "Pour localiser une fuite hydraulique, il faut passer la main sur les flexibles suspects", False),
            (22, "Lorsqu'une batterie au plomb est en charge, elle produit des gaz qui créent un risque d'explosion", True),
            (23, "Lors de l'utilisation des engins compacts, le conducteur est autorisé à actionner les commandes depuis l'extérieur du poste de conduite", False),
            (24, "Le levier de sécurité doit être en position relevée à chaque fois que le conducteur descend de l'engin", True),
            (25, "Pendant le gonflage, il faut se positionner à 3 m devant le pneumatique", False),
            (26, "Les pneumatiques peuvent être sujets à des variations de pression importantes", True),
            (27, "Pour une meilleure visibilité sur la zone de travail, il faut se rapprocher au maximum des bords de fouilles", False),
            (28, "En circulation sur talus, il faut vider le godet du côté haut de la pente", False),
            (29, "Avec une chargeuse, cette méthode d'élingage est recommandée", True),
            (30, "Cet abaque permet de déterminer la capacité de levage de la pelle", True),
            (31, "L'adhérence des chenilles est identique à celle des pneumatiques", False),
            (32, "L'écartement des rampes doit être vérifié avant de charger l'engin sur le porte-engins", True),
            (33, "Un grillage avertisseur de couleur verte signale une canalisation de gaz", False),
            (34, "La distance minimale qui doit être respectée avec un conducteur nu sous tension de moins de 50 000 V est de 3 mètres", True),
            (35, "La consommation de cannabis aide le conducteur à accomplir ses tâches de façon plus sûre", False),
            (36, "L'employeur peut interdire à un conducteur en état d'ivresse de conduire", True),
            (37, "Le risque de perte d'attention lors d'un appel est minimisé si le conducteur a l'habitude d'utiliser un téléphone mobile", False),
            (38, "Lors de la conduite d'engin, l'utilisation d'écouteurs crée des risques", True),
            (39, "Recharger les batteries des engins électriques dans un environnement clos ne présente pas de risques", False),
            (40, "Il est interdit de fumer ou de téléphoner en faisant le plein de carburant", True),
            (41, "Se laver les mains avec du carburant ne crée aucun risque", False),
            (42, "L'utilisation de solvants de nettoyage peut générer des risques chimiques", True),
            (43, "Les engins électriques émettent autant de bruit que les engins thermiques", False),
            (44, "Limiter les vibrations transmises au conducteur réduit les risques de lombalgie", True),
        ],
        4: [
            (1,  "Ce panneau impose de circuler à une vitesse minimum de 50 km par heure", False),
            (2,  "Les séparateurs de chaussée permettent le balisage des zones de travaux et la séparation des circulations", True),
            (3,  "Ce geste signifie que le conducteur doit lever la benne à cet endroit", False),
            (4,  "Le signaleur indique de baisser la charge", True),
            (5,  "La distance d'arrêt d'un engin en charge est plus importante sur sol sec que sur piste mouillée", False),
            (6,  "Lors du déplacement d'une charge suspendue, elle doit être aussi près du sol que possible", True),
            (7,  "En circulation, garder une distance de sécurité avec l'engin qui précède est une perte de temps", False),
            (8,  "La distance de sécurité doit être augmentée en cas de mauvaises conditions météorologiques", True),
            (9,  "Après un dépassement, il faut se réinsérer le plus vite possible pour obliger l'autre engin à ralentir", False),
            (10, "Avant le dépassement d'un autre engin, il faut contrôler dans les rétroviseurs que la manœuvre peut être réalisée sans danger", True),
            (11, "Sur la voie publique, la vitesse d'un engin de chantier est limitée à 40 km/h", False),
            (12, "Sur la voie publique, un engin de chantier doit être équipé d'un gyrophare orange", True),
        ],
        5: [
            (1,  "En fin de poste, il faut laisser les clés de contact sur l'engin", False),
            (2,  "Pour éviter la condensation dans le réservoir, il est préférable de faire le plein de carburant en fin de journée", True),
            (3,  "En fin de poste, le conducteur n'est pas tenu de signaler la présence d'un témoin rouge d'alerte allumé au tableau de bord de l'engin", False),
            (4,  "Le conducteur ne doit pas utiliser un compacteur dont les freins sont défaillants", True),
        ],
    },

    3: {
        1: [
            (1,  "Lors de la vente d'un engin neuf, le constructeur doit le livrer avec une notice d'instructions", True),
            (2,  "L'employeur doit tenir à jour un carnet de maintenance pour les engins qui sont utilisés pour réaliser des opérations de levage", True),
            (3,  "La formation du conducteur n'est pas de la responsabilité de l'employeur", False),
            (4,  "Le conducteur peut être pénalement responsable d'un accident qu'il a causé", True),
            (5,  "La détention du CACES® est suffisante pour conduire un engin de chantier", False),
            (6,  "Sauf prescriptions contraires, le conducteur doit toujours mettre la ceinture de sécurité lors de l'utilisation d'un engin de chantier à conducteur porté", True),
            (7,  "Le chef de chantier est le seul responsable de la vérification lors de la prise de poste des engins de son chantier", False),
            (8,  "Un élingueur doit être spécifiquement formé à l'élingage des charges", True),
            (9,  "La mission principale de l'OPPBTP est un rôle de conseil en prévention", True),
            (10, "Une des missions de la [Carsat/Cramif/CGSS] est d'assurer les salariés en cas d'accident du travail", True),
            (11, "Une pelle hydraulique de masse inférieure ou égale à 6000 kg appartient à la catégorie A de la recommandation CACES® R.482", True),
            (12, "Cet engin de masse en service 2,5 tonnes et de charge utile 3 tonnes est un engin de transport qui appartient à la catégorie E de la recommandation CACES® R.482", True),
        ],
        2: [
            (1,  "Cette partie de l'engin est la tourelle", True),
            (2,  "Dans un train de chenilles, la roue motrice est appelée « barbotin »", True),
            (3,  "Les engins ne peuvent pas se déplacer à plus de 25 km/h", False),
            (4,  "La capacité nominale d'un engin de levage est le poids maximum qu'il peut soulever", False),
            (5,  "Le circuit de refroidissement du moteur thermique permet également d'assurer le chauffage de la cabine de l'engin", True),
            (6,  "Sur un engin, le blocage du différentiel impose aux roues motrices de tourner à la même vitesse", True),
            (7,  "Sur cette chaîne cinématique de bouteur, [1] est le moteur thermique", True),
            (8,  "Un tombereau s'arrête immédiatement lorsqu'on lève le pied de l'accélérateur", False),
            (9,  "Les vérins de levage sont des vérins de sécurité qui ne peuvent jamais présenter de fuites", False),
            (10, "La lubrification d'un moteur de compacteur n'est pas nécessaire", False),
            (11, "L'équipement installé à l'arrière de cette niveleuse est un scarificateur", True),
            (12, "Cette tarière qui équipe une pelle hydraulique n'est pas un équipement interchangeable", False),
            (13, "Lorsqu'il est en position baissée, l'accoudoir de gauche neutralise toutes les commandes hydrauliques", True),
            (14, "Sur toutes les pelles hydrauliques, les manipulateurs [3] et [7] commandent toujours les mêmes mouvements", False),
            (15, "Tous les engins de chantier sont équipés d'un gyrophare", False),
            (16, "Les protecteurs installés sur les foreuses limitent les risques de happement par les éléments mobiles", True),
            (17, "Lorsqu'il n'y a pas de risques de chute d'objets, il est autorisé d'utiliser un engin dont la cabine est endommagée", False),
            (18, "La structure TOPS protège le conducteur en cas de basculement de l'engin", True),
            (19, "Dans les engins de chantier à déplacement lent, le port de la ceinture de sécurité n'est pas obligatoire", False),
            (20, "Le conducteur doit verrouiller sa ceinture dès qu'il s'installe sur le siège", True),
            (21, "Les amortisseurs de siège ne s'usent jamais", False),
            (22, "Un siège dont la suspension est correctement réglée permet de réduire le risque de TMS (troubles musculosquelettiques)", True),
            (23, "Lorsque ce voyant est allumé, le conducteur peut approcher le godet à n'importe quelle distance d'une ligne aérienne", False),
            (24, "Ce panneau impose le port de chaussures de sécurité", True),
            (25, "Plus le centre de gravité de l'engin est haut, plus sa stabilité latérale est importante", False),
            (26, "La circulation avec le godet en hauteur peut causer le renversement d'un engin", True),
            (27, "Sur un terrain plat, le conducteur d'une chargeuse peut circuler avec le godet levé pour améliorer la visibilité", False),
            (28, "Sur les talus très inclinés, le conducteur doit circuler en suivant la ligne de la plus grande pente", True),
        ],
        3: [
            (1,  "Le plan de circulation du chantier doit séparer au maximum les flux des engins et des piétons", True),
            (2,  "Sur le chantier le conducteur, même prioritaire, doit rester attentif dans sa zone d'évolution", True),
            (3,  "Il est inutile de regarder derrière si l'engin est équipé d'un signal sonore de recul", False),
            (4,  "Le conducteur peut passer l'équipement au dessus d'un opérateur situé dans une tranchée", False),
            (5,  "Lors d'une marche arrière dans une zone sans visibilité, le conducteur doit obligatoirement rester en contact visuel avec son chef de manœuvre", True),
            (6,  "Se faire guider lors d'une manœuvre sans visibilité permet de réduire le risque d'accident", True),
            (7,  "Pour effectuer une manœuvre en travail de nuit, il suffit de recourir à un chef de manœuvre", False),
            (8,  "Pour mieux voir la zone de travail, le conducteur peut se lever du siège pendant le déplacement de l'engin", False),
            (9,  "Il est interdit de transporter du personnel dans la benne d'un motobasculeur", True),
            (10, "Si la place est suffisante dans la cabine, le conducteur peut transporter un collègue debout à côté de lui", False),
            (11, "Le chef de chantier est autorisé à transporter du personnel avec n'importe quel engin", False),
            (12, "L'élévation de personnel avec un engin de chantier est toujours interdite, même si les vérins sont équipés de clapets anti-retour", False),
            (13, "Le conducteur d'une pelle peut élever une personne dans le godet jusqu'à une hauteur de 1,50 m", False),
            (14, "Si le conducteur est titulaire du CACES® R.486 (PEMP) en plus du CACES® R.482, il est autorisé à élever du personnel avec un engin de chantier", False),
            (15, "En cas de perte de contrôle de l'engin, le conducteur doit poser le plus vite possible l'équipement au sol", True),
            (16, "Avec un tombereau, le rapport de boîte utilisé pour descendre une pente est différent de celui qui est utilisé pour la monter", True),
            (17, "Pour garder le contrôle de l'engin, il faut maintenir un régime moteur le plus faible possible", False),
            (18, "L'accès au train de tiges des foreuses doit être empêché ou limité pendant la phase de forage", True),
            (19, "L'ouverture des capots moteur avec le moteur tournant est une opération à risques", True),
            (20, "Le réglage des courroies doit se faire avec le moteur tournant lentement", False),
            (21, "Contrôler le niveau de liquide de refroidissement de l'engin avec le moteur tournant ne présente pas de risques", False),
            (22, "Pour rechercher l'origine d'une fuite hydraulique, l'opérateur doit porter des gants adaptés et des lunettes de protection", True),
            (23, "Le démarrage du moteur doit être effectué avec les commandes en position neutre", True),
            (24, "Il n'existe pas de risque à circuler ou stationner à proximité immédiate d'un engin", False),
            (25, "Si l'opérateur porte des EPI, il n'y a aucun risque lors du gonflage d'un pneumatique", False),
            (26, "Lorsque la roue n'est pas sur l'engin, il est préconisé d'utiliser une cage de gonflage", True),
            (27, "Pour travailler au sommet d'un talus, le positionnement de la pelle à chenilles est effectué parallèlement à la ligne de crête", False),
            (28, "Lors de travaux en bord de talus, les vibrations causées par l'engin créent des risques d'éboulement", True),
            (29, "Avec une pelle dont les vérins de flèche ne sont pas équipés de clapets de sécurité, il est autorisé d'effectuer le levage de charges très légères", False),
            (30, "Un engin de terrassement ne peut pas être utilisé pour effectuer une opération de levage si son abaque de charge n'est pas affiché en cabine", True),
            (31, "Lorsqu'un engin est transporté sur un porte-engins, il faut toujours laisser la clé sur le contact", False),
            (32, "La détention d'une autorisation de conduite correspondant à la catégorie G de la recommandation CACES® R.482 permet de charger un engin sur un porte-engin", False),
            (33, "L'amorçage d'un engin avec une ligne électrique ne crée aucun risque", False),
            (34, "En cas de forte pluie ou de dégel, le risque d'instabilité du sol impose de prendre des précautions particulières lors de la conduite des engins de chantier", True),
            (35, "Lorsque c'est son médecin qui le lui a prescrit, cela ne crée aucun risque qu'un conducteur d'engin prenne un médicament dont l'emballage comporte ce pictogramme", False),
            (36, "La consommation de substances psycho actives (alcool, produits stupéfiants…) par le conducteur a une influence sur son comportement", True),
            (37, "L'écoute de musique avec des écouteurs pendant la conduite de l'engin permet au conducteur de rester plus concentré", False),
            (38, "L'employeur peut interdire aux conducteurs d'utiliser un téléphone mobile pendant les phases de travail", True),
            (39, "Tous les engins sont équipés d'un ou plusieurs extincteurs", False),
            (40, "Pour travailler dans des locaux fermés ou peu ventilés, il est recommandé de recourir à des engins électriques", True),
            (41, "Cela ne crée aucun risque de transporter du carburant supplémentaire dans un jerrican", False),
            (42, "Il ne faut jamais transvaser un solvant de son emballage d'origine dans une bouteille d'eau", True),
            (43, "Lorsque les pistes d'un chantier sont en mauvais état, cela n'a pas de conséquences sur le niveau des vibrations transmises au conducteur", False),
            (44, "Maintenir les portes et les vitres de l'engin fermées permet de réduire le niveau sonore au poste de conduite", True),
        ],
        4: [
            (1,  "Ce panneau prévient d'une succession de virages dangereux", True),
            (2,  "Lorsqu'il est situé aux abords d'un obstacle, ce panneau impose de le contourner par la gauche", False),
            (3,  "Ce geste signifie « fin de prise de commandement »", True),
            (4,  "Le signaleur indique la direction à suivre", True),
            (5,  "La masse de la charge transportée n'a aucune incidence sur la distance de freinage", False),
            (6,  "Sur une même piste, les engins qui circulent en charge ont la priorité sur les engins qui circulent à vide", True),
            (7,  "En circulation, lorsque la piste est mouillée, cela n'a aucune incidence sur la distance de sécurité à maintenir entre deux engins qui se suivent", False),
            (8,  "La distance de sécurité à conserver entre deux engins en circulation qui se suivent dépend de leur vitesse de déplacement", True),
            (9,  "Lors d'un dépassement, il est indispensable d'utiliser le rétroviseur", True),
            (10, "Avant d'effectuer le dépassement d'un autre engin, le conducteur doit vérifier que la largeur de la piste le permet", True),
            (11, "Pour pouvoir se déplacer sur la voie publique, un engin de chantier doit être immatriculé", False),
            (12, "Lorsqu'une chargeuse-pelleteuse est en transfert sur la voie publique, le godet de chargement doit être en position basse", True),
        ],
        5: [
            (1,  "A chaque prise de poste, le conducteur doit vérifier le gonflage des pneus de l'engin", True),
            (2,  "En fin de poste, l'engin doit être stationné avec l'équipement le plus haut possible", False),
            (3,  "En cas de panne sur un chantier, le conducteur doit immédiatement improviser un dépannage de fortune", False),
            (4,  "Le conducteur doit immédiatement signaler toute anomalie dans le fonctionnement de l'engin", True),
        ],
    },

    4: {
        1: [
            (1,  "Le constructeur est responsable de la conformité de l'engin lors de sa mise sur le marché", True),
            (2,  "L'employeur est responsable de la mise à disposition d'un engin conforme", True),
            (3,  "Le constructeur de l'engin est responsable de la tenue du carnet de maintenance et d'entretien", False),
            (4,  "Le conducteur n'est pas responsable du maintien en bon état de l'engin qu'il utilise", False),
            (5,  "Le conducteur ne peut pas refuser d'effectuer une manœuvre qu'il juge dangereuse", False),
            (6,  "Pour être autorisé à conduire un engin, le conducteur doit être informé des risques liés à son environnement de travail", True),
            (7,  "Les VGP (vérifications générales périodiques) sont toujours réalisées par le chef de chantier", False),
            (8,  "Le signaleur est une personne formée et désignée par le chef d'établissement", True),
            (9,  "Le contrôleur de la [Carsat/Cramif/CGSS] s'assure des bonnes conditions de travail des salariés", True),
            (10, "Lorsqu'il constate une situation de travail dangereuse, un inspecteur du travail ne peut pas arrêter un chantier", False),
            (11, "Une autorisation de conduite de catégorie A selon la recommandation CACES® R.482 permet de conduire une pelle compacte de masse 5 tonnes", True),
            (12, "Un finisseur appartient à la catégorie D de la recommandation CACES® R.482", False),
        ],
        2: [
            (1,  "Cette partie de la pelle fait office de contrepoids", True),
            (2,  "[1] est la flèche", True),
            (3,  "La charge utile d'un engin de transport s'exprime en mètres cubes", False),
            (4,  "Le tableau de charge d'un engin doit être présent au poste de conduite", True),
            (5,  "Le convertisseur de couple est un composant de la chaîne cinématique", True),
            (6,  "Le frein de stationnement peut être à commande électrique ou manuelle", True),
            (7,  "Sur un engin, le différentiel permet aux roues d'un même essieu de tourner à une vitesse de rotation différente", True),
            (8,  "Ce schéma représente un vérin double effet", True),
            (9,  "Sur un engin de chantier, le convertisseur de couple et la boite de vitesses ne nécessitent aucun entretien", False),
            (10, "La commande du système de freinage est identique sur tous les engins de chantier", False),
            (11, "Lorsqu'elle est adaptée à l'engin, une benne preneuse peut être mise en place sur une pelle hydraulique", True),
            (12, "Un ripper s'utilise généralement pour des travaux sur des terrains très meubles ou sablonneux", False),
            (13, "Un conducteur ne doit pas utiliser un engin lorsque l'identification des organes de commande du poste de conduite est absente ou détériorée", True),
            (14, "Ces deux manettes commandent le mouvement de translation de l'engin", True),
            (15, "La cage installée sur une foreuse sert principalement à protéger les opérateurs des projections de matériaux", True),
            (16, "Les rétroviseurs cassés doivent être remplacés", True),
            (17, "Une structure FOPS protège le conducteur en cas de retournement de l'engin", False),
            (18, "La grille en face avant de la cabine protège le conducteur des projections de matériaux", True),
            (19, "Dans la cabine d'un engin de chantier, le port de la ceinture de sécurité n'est obligatoire que lors de la circulation sur la voie publique", False),
            (20, "Une ceinture de sécurité endommagée doit immédiatement être remplacée", True),
            (21, "Dans un engin de compactage, les réglages du siège sont inutiles", False),
            (22, "Lorsque cela est possible, il est primordial que le conducteur adapte le réglage du siège de l'engin à sa morphologie", True),
            (23, "Sur une chargeuse articulée, ce pictogramme indique la position à adopter pour vérifier la pression des pneus", False),
            (24, "Ce pictogramme signifie qu'il est nécessaire de prendre connaissance de la notice d'utilisation", True),
            (25, "L'engin doit se déplacer perpendiculairement à une pente", False),
            (26, "Circuler sur un talus peut provoquer le renversement de l'engin", True),
            (27, "Avec un engin muni de stabilisateurs, il n'est pas nécessaire de les déployer pour réaliser une tranchée de faibles dimensions", False),
            (28, "Une surcharge de l'engin peut causer son basculement frontal", True),
        ],
        3: [
            (1,  "Les engins peuvent être équipés de caméras de recul pour améliorer la visibilité arrière pour le conducteur", True),
            (2,  "Le conducteur ne doit pas utiliser un engin dont l'avertisseur de recul ne fonctionne pas", True),
            (3,  "Sur un chantier, un engin qui arrive de la droite est toujours prioritaire", False),
            (4,  "Un angle mort est la zone qui est visible dans un rétroviseur", False),
            (5,  "Lors d'une manœuvre dans une zone sans visibilité, le conducteur doit effectuer une reconnaissance à pied de cette zone", True),
            (6,  "Manœuvrer à vitesse lente permet de réduire le risque de heurt", True),
            (7,  "Lors d'un déplacement sur la voie publique le conducteur doit toujours allumer les feux de route de l'engin", False),
            (8,  "Un manque de visibilité ne peut pas occasionner le renversement de l'engin", False),
            (9,  "Le transport de personnel est autorisé lorsque l'engin est équipé d'un siège supplémentaire prévu par le constructeur", True),
            (10, "Lorsqu'il est transporté dans une cabine équipée à cet effet, un passager doit être titulaire d'une autorisation de conduite", False),
            (11, "Il est autorisé de transporter un compagnon s'il est sur le marchepied de l'engin et qu'il se tient fermement aux poignées", False),
            (12, "Il est interdit d'élever du personnel sur les bras de fourche d'un chariot de manutention", True),
            (13, "L'élévation de personnel dans le godet d'une chargeuse est autorisée avec l'accord du chef de chantier", False),
            (14, "Si l'engin est équipé de clapets anti retour sur les vérins de flèche et de balancier, le conducteur peut élever un compagnon dans le godet", False),
            (15, "En descente, l'utilisation du ralentisseur permet de maîtriser la vitesse", True),
            (16, "Le conducteur doit accélérer avant d'aborder une descente", False),
            (17, "Les boites de vitesse type « Powershift » améliorent l'efficacité du frein moteur", False),
            (18, "Les éléments de protection des parties mobiles qui sont endommagés doivent être immédiatement remplacés", True),
            (19, "Le graissage des cardans doit se faire moteur à l'arrêt", True),
            (20, "Si l'engin est équipé de clapets de sécurité, il n'est pas nécessaire de caler les équipements lors d'une intervention sur le circuit hydraulique", False),
            (21, "L'ouverture d'un réservoir hydraulique dont le liquide est chaud ne présente aucun risque", False),
            (22, "Pour raccorder une batterie à un engin, l'opérateur doit d'abord brancher la cosse [+]", True),
            (23, "Les clapets de sécurité protègent contre une descente inopinée de l'équipement en cas de rupture d'un flexible hydraulique", True),
            (24, "Une action involontaire sur l'un des organes de service de l'engin peut provoquer un mouvement de l'équipement", True),
            (25, "Lorsqu'il regonfle les pneumatiques d'un engin, le conducteur doit se positionner face à la roue afin de ne pas tordre le flexible du compresseur", False),
            (26, "Le risque principal lors du gonflage est l'éclatement du pneumatique", True),
            (27, "Le blindage des tranchées n'est pas obligatoire lorsque la profondeur est inférieure à 2,30 m", False),
            (28, "La pluie peut déstabiliser les bords d'une fouille", True),
            (29, "La capacité de levage maximum d'un chariot à portée variable est obtenue lorsque le télescope est entièrement déployé", False),
            (30, "Ce crochet est destiné au levage de charges", True),
            (31, "Pour parcourir une courte distance, il n'est pas nécessaire d'arrimer l'engin sur le porte-engins", False),
            (32, "Avant de commencer le chargement de l'engin, le porte-engins doit être positionné sur un terrain plat et résistant, immobilisé et ses roues calées", True),
            (33, "Les réseaux enterrés de gaz sont toujours identifiés et positionnés avec un haut niveau de précision", False),
            (34, "Tout conducteur d'engin amené à effectuer des travaux à proximité de réseaux doit être titulaire d'une AIPR (autorisation d'intervention à proximité des réseaux)", True),
            (35, "Boire un verre de vin à la pause déjeuner n'augmente pas le risque d'accident", False),
            (36, "Certains médicaments peuvent avoir un effet néfaste sur l'attention du conducteur d'engin", True),
            (37, "Pendant la conduite d'engin, utiliser un téléphone mobile avec un kit mains libres ne crée pas de risque", False),
            (38, "De façon générale, il est interdit de répondre au téléphone en manœuvrant un engin", True),
            (39, "Le ravitaillement d'un engin en liquide de refroidissement doit être réalisé moteur chaud", False),
            (40, "Les gaz d'échappement des engins à moteur Diesel sont nocifs", True),
            (41, "Un conducteur d'engin n'est pas concerné par les risques chimiques", False),
            (42, "Seuls les détergents normalisés doivent être utilisés", True),
            (43, "La conduite d'engin en position debout expose moins le conducteur aux vibrations", False),
            (44, "Ce pictogramme indique le niveau sonore mesuré à l'extérieur de l'engin", True),
        ],
        4: [
            (1,  "Ce panneau de signalisation temporaire indique la fin du chantier", False),
            (2,  "Un panneau rond et cerclé de rouge sur un chantier indique une interdiction", True),
            (3,  "Ce geste indique la taille de la charge à lever", False),
            (4,  "Le signaleur demande de reculer", True),
            (5,  "Avec une pelle en charge, il faut monter et descendre les pentes en marche avant", False),
            (6,  "La distance de freinage est augmentée lorsque l'engin est chargé", True),
            (7,  "Sur une piste roulante, la distance minimale de sécurité entre deux tombereaux qui se suivent est de 20 mètres", False),
            (8,  "La distance de sécurité entre deux engins en charge qui se suivent doit être plus importante sur une piste mouillée que sur un sol sec", True),
            (9,  "Une manœuvre de dépassement ne présente aucun risque", False),
            (10, "Avant de procéder au dépassement d'un autre engin, il faut actionner le clignotant s'il existe", True),
            (11, "En l'absence de dispositions particulières, le Code de la route limite la largeur des engins à 2,70 m", False),
            (12, "Sur la voie publique, les engins doivent comporter à l'arrière un disque indiquant leur limitation de vitesse", True),
        ],
        5: [
            (1,  "En fin de poste, l'engin doit être stationné sur une voie de circulation", False),
            (2,  "A chaque prise de poste, le conducteur vérifie que l'enclenchement et le verrouillage du godet ou de l'outil sur l'attache rapide sont corrects", True),
            (3,  "Le conducteur n'est pas tenu de signaler un rétroviseur endommagé", False),
            (4,  "Un engin dont l'avertisseur sonore de recul ne fonctionne plus ne doit pas être utilisé", True),
        ],
    },

    5: {
        1: [
            (1,  "Le marquage CE de l'engin relève de la responsabilité de l'employeur", False),
            (2,  "L'employeur doit mettre à la disposition du conducteur un engin conforme à la réglementation", True),
            (3,  "Pour un intérimaire, l'autorisation de conduite est délivrée par le responsable de l'entreprise utilisatrice", True),
            (4,  "Le conducteur doit respecter les règles d'utilisation de l'engin qui lui ont été communiquées lors de la formation à la conduite", True),
            (5,  "S'il heurte un piéton lorsqu'il manœuvre l'engin, le conducteur n'est pas responsable", False),
            (6,  "La formation à la conduite n'est pas obligatoire pour les conducteurs d'engins de chantier", False),
            (7,  "Le chef de chantier est responsable de la sécurité sur le chantier", True),
            (8,  "Le signaleur est responsable de l'élingage", False),
            (9,  "Un contrôleur de la [Carsat/Cramif/CGSS] peut délivrer l'autorisation de conduite au conducteur", False),
            (10, "L'inspecteur du travail peut vérifier les autorisations de conduite des conducteurs de l'entreprise", True),
            (11, "Un compacteur de masse supérieure à 6000 kg appartient à la catégorie D de la recommandation CACES® R.482", True),
            (12, "Un chariot de manutention tout terrain compact appartient à la catégorie A de la recommandation CACES® R.482", True),
        ],
        2: [
            (1,  "Cet organe est un essieu ferroviaire", False),
            (2,  "Cette partie de la charpente est le balancier", True),
            (3,  "Sur un engin de transport, la charge utile est le résultat de la soustraction PTAC - PV", True),
            (4,  "Les dimensions d'un engin sont toujours indiquées sur la plaque constructeur", False),
            (5,  "Une boîte de vitesses « power shift » permet de passer d'une vitesse à une autre sans arrêter la transmission du mouvement", True),
            (6,  "Sur ce schéma hydraulique, la tige du vérin rentre", True),
            (7,  "Le carter sert de réservoir d'huile moteur", True),
            (8,  "Sur une chargeuse-pelleteuse, le différentiel permet de rouler plus vite", False),
            (9,  "Le moteur thermique d'un engin ne possède pas de système de refroidissement", False),
            (10, "Cet engin ne comporte pas de frein de stationnement", False),
            (11, "Cet équipement est un palonnier destiné à la manutention de rails, en particulier destiné aux pelles rail-route", False),
            (12, "Une plaque vibrante peut être installée sur tout type de pelle hydraulique, sans précautions particulières", False),
            (13, "Cet organe de service commande l'avertisseur sonore (klaxon)", False),
            (14, "Le manipulateur de droite [7] commande la montée-descente de la flèche et l'ouverture-fermeture du godet", False),
            (15, "Tous les engins de chantier sont équipés d'un bouton d'arrêt d'urgence au poste de commande", False),
            (16, "Lorsqu'un engin n'est pas utilisé, la clé doit être ôtée du contact", True),
            (17, "Sur un engin de chantier, la structure de protection ne peut pas être à la fois ROPS et FOPS", False),
            (18, "Une structure ROPS résiste en cas de retournement de l'engin", True),
            (19, "Lorsque la porte de la cabine est fermée, il est inutile d'attacher sa ceinture de sécurité pendant le travail", False),
            (20, "Dans un engin équipé d'une cabine ROPS, le port de la ceinture de sécurité est obligatoire", True),
            (21, "Il n'est pas utile de régler le siège d'un engin compact", False),
            (22, "Les réglages du siège permettent notamment au conducteur d'être correctement positionné par rapport aux organes de commande", True),
            (23, "Ce pictogramme identifie les points d'arrimage de l'engin", False),
            (24, "Ce voyant concerne la pression d'huile moteur", True),
            (25, "Une charge mal centrée peut être à l'origine du renversement de l'engin", True),
            (26, "Se déplacer selon la ligne de plus grande pente réduit les risques de renversement de l'engin", False),
            (27, "La position du centre de gravité de l'engin est identique quelque soit la charge dans le godet", False),
            (28, "Circuler avec une charge haute peut provoquer le basculement de l'engin", True),
        ],
        3: [
            (1,  "A la mise en route de l'engin, le conducteur doit vérifier que les rétroviseurs sont propres et bien réglés", True),
            (2,  "Le conducteur ne doit jamais déplacer une charge au dessus d'un personnel au sol", True),
            (3,  "Pour améliorer la visibilité, le conducteur peut se pencher par la fenêtre ouverte de son engin", False),
            (4,  "Le risque de heurt de personnes existe principalement en marche avant", False),
            (5,  "Il est interdit de déplacer une charge sans visibilité sur la zone de manœuvre", True),
            (6,  "Un éclairage insuffisant lors d'une manœuvre peut être à l'origine d'un accident", True),
            (7,  "Lors d'une marche arrière dans une zone sans visibilité, le chef de manœuvre doit se tenir devant l'engin", False),
            (8,  "Lors d'une manœuvre sans visibilité, klaxonner suffit à supprimer le risque de heurt de personnes", False),
            (9,  "Dans un tombereau équipé d'un second siège avec ceinture, le conducteur peut transporter un collègue qui ne dispose pas du permis de conduire", True),
            (10, "Même sur une courte distance, il est interdit de transporter une personne sur le marchepied d'un engin de chantier", True),
            (11, "Le chef de chantier peut imposer au conducteur de le transporter sur l'engin", False),
            (12, "Il est interdit de se faire élever sur les bras de fourche d'un chariot élévateur", True),
            (13, "Le conducteur titulaire d'une autorisation de conduite peut effectuer du levage de personnel avec un engin de chantier", False),
            (14, "Il est autorisé d'élever une personne dans le godet d'une chargeuse pour réaliser un travail en hauteur de courte durée", False),
            (15, "Pour réduire le risque de perte de contrôle de l'engin, le conducteur doit sélectionner un rapport de boîte qui offre le meilleur frein moteur possible", True),
            (16, "En descente, le conducteur doit utiliser le frein de service le plus souvent possible", False),
            (17, "En cas de perte de contrôle de l'engin, le conducteur doit détacher sa ceinture pour être libre de ses mouvements", False),
            (18, "La vérification de la tension de la courroie d'alternateur doit être effectuée moteur arrêté", True),
            (19, "Porter des vêtements flottants à proximité d'un arbre de transmission en mouvement peut causer un accident grave ou mortel", True),
            (20, "En utilisant le mode de fonctionnement réduit, le conducteur peut intervenir seul pour débloquer la tige de forage d'une foreuse", False),
            (21, "Les batteries des engins électriques ne créent aucun risque d'origine électrique", False),
            (22, "Faire le plein de carburant d'un engin lorsque le moteur est chaud ne présente pas de risque", False),
            (23, "Afin d'obtenir une meilleure visibilité depuis la cabine, le conducteur peut se lever de son siège pour conduire l'engin", False),
            (24, "Décompresser le circuit hydraulique après l'arrêt de l'engin peut éviter un mouvement intempestif de l'équipement", True),
            (25, "Il n'y a plus aucun risque d'éclatement du pneumatique lorsqu'il est placé dans une cage de gonflage", False),
            (26, "Il est impératif de rester éloigné à plus de 3 m d'un pneumatique en cours de gonflage", False),
            (27, "En cavage, il est autorisé de creuser avec précautions sous les points d'appui de l'engin (pneumatiques ou chenilles)", False),
            (28, "Lors de travaux en bord de talus, les stabilisateurs doivent être déployés de sorte que le châssis de l'engin soit horizontal", True),
            (29, "Les élingues à usage unique peuvent être utilisées pour réaliser des manutentions jusqu'à ce qu'elles commencent à s'effilocher", False),
            (30, "Une pelle hydraulique sur chenilles peut être utilisée pour effectuer une opération de levage si elle est équipée de clapets de sécurité sur la flèche et le balancier", True),
            (31, "Lorsqu'un engin est positionné sur un porte-engins, le godet doit demeurer en position haute", False),
            (32, "La zone de chargement/déchargement de l'engin doit être délimitée et balisée", True),
            (33, "Le conducteur peut approcher le godet de la chargeuse à 4 m d'une ligne électrique aérienne sous tension de plus de 50 kV", False),
            (34, "En cas de découverte de munitions de guerre, les travaux de terrassement doivent être interrompus dès la découverte de l'objet suspect", True),
            (35, "Une faible consommation d'alcool peut améliorer la vigilance du conducteur", False),
            (36, "Lorsqu'un cariste prend un médicament dont l'emballage comporte ce pictogramme, il est conseillé qu'il sollicite l'avis du service de prévention et de santé au travail", True),
            (37, "Pour masquer le bruit du moteur, il est recommandé au conducteur d'un engin de chantier d'écouter de la musique à l'aide d'un casque audio", False),
            (38, "Téléphoner avec un kit mains libres pendant la conduite d'un engin crée des risques", True),
            (39, "Il est autorisé de fumer dans un atelier d'entretien et de réparation d'engins", False),
            (40, "Approcher une flamme nue à proximité d'une batterie en charge peut provoquer une explosion", True),
            (41, "Un solvant de nettoyage usagé peut être jeté dans un évier", False),
            (42, "Le contact de la peau avec des produits pétroliers crée des risques pour la santé", True),
            (43, "La perte d'audition occasionnée par une exposition à un niveau sonore excessif est réversible", False),
            (44, "Un siège dont l'amortissement est correctement réglé réduit significativement les vibrations transmises au conducteur", True),
        ],
        4: [
            (1,  "Les panneaux de signalisation routière dont le fond est blanc ont un caractère temporaire", False),
            (2,  "Ce panneau triangulaire à bord rouge indique un danger", True),
            (3,  "Ce geste signifie que le conducteur doit poser la charge au sol", False),
            (4,  "Le signaleur indique la fin de sa prise de commandement", True),
            (5,  "Il faut rouler avec la charge en position haute afin d'améliorer la visibilité", False),
            (6,  "La distance d'arrêt d'un engin en charge est augmentée sur piste mouillée", True),
            (7,  "La distance de sécurité entre deux engins en circulation qui se suivent dépend de leur puissance", False),
            (8,  "La distance de sécurité a une influence sur le risque de collision entre engins", True),
            (9,  "Il est toujours autorisé de dépasser un engin à chenilles par la droite", False),
            (10, "Pour dépasser un autre engin, le conducteur doit respecter les consignes du plan de circulation du chantier", True),
            (11, "Un engin sur chenilles peut circuler sur la voie publique jusqu'à 25 km/h", False),
            (12, "Lorsqu'un engin circule sur la voie publique, la longueur maximale autorisée est de 15 m", False),
        ],
        5: [
            (1,  "En fin de poste, il n'est pas nécessaire que le conducteur vérifie la bonne fermeture des capots de l'engin puisqu'il vient de l'utiliser pendant plusieurs heures", False),
            (2,  "En début de poste, le conducteur doit s'assurer de l'absence d'anomalies sur le tableau de bord de l'engin", True),
            (3,  "Un conducteur de pelle n'est pas tenu de signaler les incidents liés au décrochage des équipements qu'il a utilisés", False),
            (4,  "Le conducteur doit signaler toute fuite d'huile importante au niveau du circuit hydraulique", True),
        ],
    },
}

# ─── Points par thème R482 ────────────────────────────────────────────────────
POINTS_THEME = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}

# Convention image : R482-G{grille}-T{theme}-Q{numero}.png ou .jpg
def get_image_url(grille: int, theme: int, question: int) -> str:
    return f"R482-G{grille}-T{theme}-Q{question}"  # sans extension, Cloudinary gère


def run():
    db = SessionLocal()
    try:
        print("=== Réinitialisation grilles R482 ===\n")

        # 1. Supprimer les utilisations existantes
        nb_util = db.query(UtilisationGrille).join(GrilleTheorie).filter(
            GrilleTheorie.famille == "R482"
        ).count()
        if nb_util > 0:
            print(f"⚠️  {nb_util} utilisation(s) de grille R482 seront supprimées.")

        # 2. Supprimer questions et grilles existantes
        grilles_existantes = db.query(GrilleTheorie).filter(
            GrilleTheorie.famille == "R482"
        ).all()

        for g in grilles_existantes:
            db.query(UtilisationGrille).filter(UtilisationGrille.grille_id == g.id).delete()
            db.query(ReponseGrille).filter(ReponseGrille.grille_id == g.id).delete()
            db.delete(g)

        db.commit()
        print(f"✅ {len(grilles_existantes)} grille(s) existante(s) supprimée(s)\n")

        # 3. Créer les 5 grilles avec leurs questions
        total_questions = 0
        for grille_num, themes in GRILLES_R482.items():
            grille = GrilleTheorie(
                famille="R482",
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
            print(f"✅ Grille {grille_num} — {nb_q} questions créées (id={grille.id})")

        print(f"\n✅ Total : {total_questions} questions pour 5 grilles R482")
        print("\nVérification :")
        for grille_num in range(1, 6):
            g = db.query(GrilleTheorie).filter(
                GrilleTheorie.famille == "R482",
                GrilleTheorie.numero == grille_num
            ).first()
            counts = {}
            for t in range(1, 6):
                c = db.query(ReponseGrille).filter(
                    ReponseGrille.grille_id == g.id,
                    ReponseGrille.theme == t
                ).count()
                counts[t] = c
            total = sum(counts.values())
            print(f"  Grille {grille_num} : T1={counts[1]} T2={counts[2]} T3={counts[3]} T4={counts[4]} T5={counts[5]} → {total}/100")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()