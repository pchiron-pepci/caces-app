from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille

db = SessionLocal()

# Textes des questions par thème (communs à toutes les grilles)
# Les questions sont les mêmes, seules les réponses changent
QUESTIONS = {
    1: [
        "Le constructeur / l'employeur : question 1",
        "Le constructeur / l'employeur : question 2",
        "Le constructeur / l'employeur : question 3",
        "Le conducteur : question 4",
        "Le conducteur : question 5",
        "Le conducteur : question 6",
        "Le chef de chantier / signaleur / elingueur : question 7",
        "Le chef de chantier / signaleur / elingueur : question 8",
        "Les acteurs en prevention : question 9",
        "Les acteurs en prevention : question 10",
        "Les types d'engins et catégories CACES® : question 11",
        "Les types d'engins et categories CACES® : question 12",
    ],
    2: [
        "Terminologie : question 1",
        "Terminologie : question 2",
        "Caracteristiques generales : question 3",
        "Caracteristiques generales : question 4",
        "Composants et mecanismes : question 5",
        "Composants et mecanismes : question 6",
        "Composants et mecanismes : question 7",
        "Composants et mecanismes : question 8",
        "Composants et mecanismes : question 9",
        "Composants et mecanismes : question 10",
        "Equipements interchangeables : question 11",
        "Equipements interchangeables : question 12",
        "Organes de service : question 13",
        "Organes de service : question 14",
        "Dispositifs de securite : question 15",
        "Dispositifs de securite : question 16",
        "Structures ROPS FOPS TOPS : question 17",
        "Structures ROPS FOPS TOPS : question 18",
        "Dispositifs de maintien conducteur : question 19",
        "Dispositifs de maintien conducteur : question 20",
        "Reglages du siege : question 21",
        "Reglages du siege : question 22",
        "Pictogrammes : question 23",
        "Pictogrammes : question 24",
        "Renversement lateral : question 25",
        "Renversement lateral : question 26",
        "Basculement frontal : question 27",
        "Basculement frontal : question 28",
    ],
    3: [
        "Heurts de personnes : question 1",
        "Heurts de personnes : question 2",
        "Heurts de personnes : question 3",
        "Heurts de personnes : question 4",
        "Manque de visibilite : question 5",
        "Manque de visibilite : question 6",
        "Manque de visibilite : question 7",
        "Manque de visibilite : question 8",
        "Transport de personnel : question 9",
        "Transport de personnel : question 10",
        "Transport de personnel : question 11",
        "Elevation de personnel : question 12",
        "Elevation de personnel : question 13",
        "Elevation de personnel : question 14",
        "Perte de controle : question 15",
        "Perte de controle : question 16",
        "Perte de controle : question 17",
        "Risques mecaniques : question 18",
        "Risques mecaniques : question 19",
        "Risques mecaniques : question 20",
        "Risques energies : question 21",
        "Risques energies : question 22",
        "Mouvement accidentel : question 23",
        "Mouvement accidentel : question 24",
        "Gonflage pneumatiques : question 25",
        "Gonflage pneumatiques : question 26",
        "Bord de fouille talus : question 27",
        "Bord de fouille talus : question 28",
        "Levage de charges : question 29",
        "Levage de charges : question 30",
        "Chargement dechargemement porte-engins : question 31",
        "Chargement dechargement porte-engins : question 32",
        "Risques environnement : question 33",
        "Risques environnement : question 34",
        "Substances psycho actives : question 35",
        "Substances psycho actives : question 36",
        "Perte d'attention telephone : question 37",
        "Perte d'attention telephone : question 38",
        "Incendie explosion gaz : question 39",
        "Incendie explosion gaz : question 40",
        "Risques chimiques : question 41",
        "Risques chimiques : question 42",
        "Bruits vibrations : question 43",
        "Bruits vibrations : question 44",
    ],
    4: [
        "Panneaux et signaux : question 1",
        "Panneaux et signaux : question 2",
        "Gestes de commandement : question 3",
        "Gestes de commandement : question 4",
        "Conditions utilisation en charge : question 5",
        "Conditions utilisation en charge : question 6",
        "Distances de securite : question 7",
        "Distances de securite : question 8",
        "Regles de depassement : question 9",
        "Regles de depassement : question 10",
        "Circulation voie publique : question 11",
        "Circulation voie publique : question 12",
    ],
    5: [
        "Verifications maintenance journalieres : question 1",
        "Verifications maintenance journalieres : question 2",
        "Conduite en cas d'incident : question 3",
        "Conduite en cas d'incident : question 4",
    ]
}

# Textes réels par grille (chaque grille a ses propres textes)
TEXTES_GRILLE = {
    1: {
        1: [
            "Le constructeur est responsable du maintien en état de conformité de l'engin",
            "L'employeur doit réaliser les VGP (vérifications générales périodiques)",
            "L'autorisation de conduite est délivrée par le constructeur de l'engin",
            "Le conducteur doit s'assurer que l'engin est en bon etat lors de la prise de poste",
            "Le conducteur peut utiliser un engin sans autorisation de conduite",
            "Pour conduire un engin de chantier, il faut obligatoirement le permis B",
            "Le signaleur doit posséder une autorisation de conduite",
            "Le chef de chantier doit veiller a la sécurite de ses équipes",
            "L'inspecteur du travail veille au respect du droit du travail",
            "Les contrôleurs de la Carsat peuvent infliger des amendes administratives",
            "Une pelle hydraulique de masse supérieure a 6000 kg appartient a la catégorie B1 de la recommandation CACES® R.482",
            "Une petite niveleuse appartient a la catégorie A de la recommandation CACES® R.482",
        ],
        2: [
            "[1] est le balancier",
            "Cette niveleuse est équipée d'un scarificateur",
            "La foreuse est un engin a déplacement alternatif",
            "La masse en service de l'engin est indiquée sur la plaque constructeur",
            "Un moteur utiliséà sans filtre à air s'use prématuremenent",
            "Ce verin situé sur le balancier de la pelle permet le mouvement du godet",
            "Le circuit de refroidissement moteur sert a maintenir le moteur a une temperature adequate",
            "Sur une chargeuse pelleteuse, le differentiel permet de rouler plus vite",
            "Sur le schema hydraulique suivant, si a=1 et b=0, alors la tige du verin rentre",
            "Dans cette chaine cinematique de chargeuse, [B] est le moteur thermique",
            "Cet equipement est une attache rapide mecanique",
            "L'utilisation d'equipements interchangeables ne nécessite pas de formation particulière",
            "Sur cette pelle hydraulique, le levier de commande [5] est un levier de translation",
            "Le relevage de la poignee rouge desactive les commandes hydrauliques",
            "Sur un crochet de levage, le linguet est facultatif",
            "L'electromodule de surveillance permet la gestion du fonctionnement du moteur, des circuits electrique et hydrostatique",
            "Une cabine ROPS protege le conducteur en cas de retournement de l'engin",
            "Le terme FOPS signifie que la cabine de l'engin est climatisee",
            "Lors de l'utilisation d'un engin de chantier equipe d'une cabine ROPS, le port de la ceinture de securite est laisse a l'appreciation du chef d'etablissement",
            "La ceinture de securite doit toujours etre utilisee",
            "Le conducteur doit regler ou verifier le reglage du siege de l'engin a la prise de poste",
            "Les vibrations mecaniques produites par les engins ne sont pas transmises au conducteur",
            "Ce voyant concerne la pression de gonflage des pneumatiques",
            "Ce voyant est un indicateur de colmatage du filtre a air",
            "La stabilite de l'engin depend de la position de son centre de gravite",
            "Un engin ne peut pas se renverser lateralement",
            "Freiner brusquement ne presente pas de risques de renversement",
            "Pour eviter de cabrer lors de la montee d'une pente importante, le poids de l'engin doit etre situe vers le haut de la rampe",
        ],
        3: [
            "Avant de proceder a une marche arriere, il est imperatif de regarder vers l'arriere ainsi que dans les retroviseurs",
            "Un angle mort est une zone qui n'est pas vue depuis le poste de conduite",
            "Le signal sonore de marche arriere supprime totalement le risque de heurt entre l'engin et une personne",
            "Lorsque le personnel a pied est interdit sur le chantier, le conducteur peut effectuer les manoeuvres sans precautions particulieres",
            "Lors de la manutention d'une charge sans visibilite, le conducteur doit etre guide par une personne formee",
            "Toutes les vitres de l'engin et tous les retroviseurs doivent etre propres et en bon etat",
            "Lorsqu'il guide un deplacement en marche arriere sans visibilite, le chef de manoeuvre doit se tenir juste derriere l'engin",
            "Avec un engin compact, le conducteur peut effectuer une marche arriere sans visibilite a faible vitesse",
            "Sur une courte distance, le conducteur peut transporter une personne debout dans la cabine de l'engin",
            "Le transport de personnel est autorise si l'engin est equipe d'un second siege avec ceinture",
            "Si l'engin possede de larges marchepieds antiderapants, il est autorise d'y transporter du personnel",
            "Il est interdit de lever des personnes avec un engin non concu a cet effet",
            "Il est autorise de lever une personne dans le godet d'un engin, avec l'accord du chef d'etablissement",
            "L'elevation de personne est autorisee avec un engin dont les VGP sont a jour et sans reserve",
            "Le conducteur doit reduire sa vitesse avant d'aborder une descente",
            "En cas de perte de controle de l'engin, le conducteur doit sauter par la porte le plus vite possible",
            "Dans une descente, pour eviter la perte de controle de l'engin, le conducteur doit mettre la boite de vitesses au point mort",
            "Les parties tournantes du moteur (ventilateurs et courroies) presentent des risques",
            "Sur une foreuse, il ne faut jamais intervenir sur un train de tiges avant l'arret complet de la rotation",
            "Occasionnellement, le graissage des cardans peut se faire moteur tournant",
            "Le demontage d'un flexible hydraulique peut etre effectue sans precautions particulieres",
            "En cas d'intervention sur le circuit electrique, il faut couper l'alimentation electrique avec le coupe-circuit",
            "Il est autorise d'agir sur les commandes d'un engin depuis le sol",
            "Sur une pelle, le levier de securite desactive les commandes de l'equipement",
            "Pour gonfler un pneu d'engin, il faut se positionner face a la roue pour bien surveiller le gonflage",
            "Le controle de la pression des pneumatiques doit toujours se faire a froid",
            "Le passage en bord de fouille avec un engin ne presente pas de danger particulier",
            "La distance a respecter par rapport a une fouille ou un talus depend des conditions meteorologiques",
            "La position correcte du crochet est celle de gauche",
            "Un cable de levage qui presente une rupture mineure doit etre immediatement remplace",
            "A defaut de rampes d'acces, il est autorise d'utiliser des planches pour le chargement d'une mini pelle sur un porte-engin",
            "Il est interdit de proceder au chargement ou au dechargement d'un engin sur un porte-engins positionne en devers",
            "Un grillage avertisseur de couleur rouge signale une canalisation d'eaux usees",
            "Lors de travaux a proximite d'une ligne electrique aerienne, le risque d'amorcage de l'arc electrique est le meme pour les engins a chenilles ou sur pneumatiques",
            "La consommation de produits stupefiants ne cree pas de risques lorsqu'elle est occasionnelle",
            "La consommation d'alcool augmente le risque d'accident",
            "Meme en phase de conduite, le conducteur doit immediatement repondre au telephone lorsque son responsable l'appelle",
            "Ecouter de la musique avec un casque reduit la vigilance du conducteur",
            "L'utilisation d'un engin a moteur Diesel a l'interieur d'un batiment ne cree aucun risque pour les salaries",
            "Il est imperatif de couper le moteur de l'engin lors du ravitaillement en carburant",
            "Lorsqu'il est vide, un bidon qui a contenu de l'AdBlue peut etre reutilise pour transporter de l'eau potable",
            "Lors de manipulation de produits hydrocarbures, l'operateur doit porter des gants de protection",
            "La vitesse de conduite n'a pas d'influence sur le niveau des vibrations transmises au conducteur",
            "Le volume sonore a partir duquel il est obligatoire de se proteger est de 85 db(A)",
        ],
        4: [
            "Sur un chantier, un panneau rond a fond bleu indique un danger",
            "Ce panneau indique un retrecissement de la chaussee",
            "Le signaleur ordonne un arret d'urgence",
            "Ce geste signifie lever la benne",
            "La distance d'arret d'un engin est plus importante lorsqu'il est a vide qu'en charge",
            "Lorsqu'il circule en descente avec un tombereau en charge, le conducteur doit selectionner le rapport de boite qui procure le meilleur frein moteur",
            "La distance de securite a conserver entre deux engins en circulation depend de la charge transportee",
            "Pour reduire les risques de collision, il est imperatif de conserver une distance de securite appropriee entre deux engins en circulation",
            "Lorsque la piste est degagee, il est permis de faire la course entre tombereaux pour augmenter la production du chantier",
            "Les regles de depassement doivent etre indiquees dans le plan de circulation du chantier",
            "La presence d'un gyrophare suffit pour etre autorise a se deplacer sur la route avec un engin",
            "La vitesse de deplacement autorisee pour un engin sur la route est de 25 km/h maximum",
        ],
        5: [
            "En debut de poste, le conducteur doit s'assurer du bon fonctionnement des freins de l'engin",
            "En fin de poste la cabine doit etre nettoyee et laissee propre",
            "Lorsqu'il constate que la date de validite de la VGP de l'engin est depassee, le conducteur doit en informer son responsable",
            "Tout incident ou defaillance doit etre signale selon la procedure en vigueur dans l'entreprise",
        ]
    }
}

# Pour les grilles 2-5, on utilise les textes de la grille 1 comme base
# (les questions sont les mêmes, seules les réponses changent)
for num_grille in range(1, 6):
    grille = db.query(GrilleTheorie).filter(
        GrilleTheorie.famille == "R482",
        GrilleTheorie.numero == num_grille
    ).first()

    if not grille:
        print(f"Grille {num_grille} non trouvee !")
        continue

    reponses = db.query(ReponseGrille).filter(
        ReponseGrille.grille_id == grille.id
    ).order_by(ReponseGrille.theme, ReponseGrille.numero_question).all()

    # Utiliser les textes de la grille 1 pour toutes les grilles
    textes = TEXTES_GRILLE.get(1, {})

    for r in reponses:
        theme_textes = textes.get(r.theme, [])
        idx = r.numero_question - 1
        if idx < len(theme_textes):
            r.texte_question = theme_textes[idx]

    db.commit()
    print(f"Grille R482 n{num_grille} - textes encodes !")

db.close()
print("Toutes les questions encodees !")