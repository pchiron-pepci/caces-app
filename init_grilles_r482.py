from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille

db = SessionLocal()

# Vérifier si déjà encodées
existing = db.query(GrilleTheorie).filter(GrilleTheorie.famille == "R482").count()
if existing > 0:
    print(f"Grilles R482 déjà en base ({existing} grilles). Suppression...")
    db.query(ReponseGrille).filter(
        ReponseGrille.grille_id.in_(
            [g.id for g in db.query(GrilleTheorie).filter(GrilleTheorie.famille == "R482").all()]
        )
    ).delete(synchronize_session=False)
    db.query(GrilleTheorie).filter(GrilleTheorie.famille == "R482").delete()
    db.commit()

# Données des 5 grilles R482
# Format : {grille_num: {theme_num: [VRAI/FAUX, ...]}}
GRILLES = {
    1: {
        1: [False, True, False, True, False, False, False, True, True, False, True, False],
        2: [False, True, False, True, True, True, True, False, False, False, True, False, True, True, False, True, True, False, False, True, True, False, False, True, True, False, False, True],
        3: [True, True, False, False, True, True, False, False, False, True, False, True, False, False, True, False, False, True, True, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        4: [False, True, True, True, False, True, False, True, False, True, False, True],
        5: [True, True, True, True],
    },
    2: {
        1: [False, True, False, True, False, True, False, False, True, False, False, True],
        2: [True, True, False, True, True, True, True, False, True, False, True, False, False, True, False, True, False, True, False, True, True, False, False, True, True, False, False, True],
        3: [True, True, False, False, True, True, False, False, False, False, False, True, False, False, True, False, False, True, True, False, False, True, False, True, False, False, False, True, False, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        4: [False, True, False, True, False, True, False, True, False, True, False, True],
        5: [False, True, False, True],
    },
    3: {
        1: [True, True, False, True, False, True, False, True, True, True, True, False],
        2: [False, True, False, True, True, True, True, False, False, False, True, False, False, True, False, True, False, True, False, True, False, True, True, False, False, True, False, True],
        3: [True, True, False, False, True, True, False, False, False, False, False, True, False, False, True, False, False, True, True, False, False, True, True, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        4: [False, True, True, True, False, True, False, True, False, True, False, True],
        5: [True, False, False, True],
    },
    4: {
        1: [True, True, False, False, False, True, False, True, True, False, True, False],
        2: [True, True, False, True, True, True, True, False, False, False, True, False, True, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        3: [True, True, False, False, True, True, False, False, False, False, False, True, False, False, True, False, False, True, True, False, False, True, True, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        4: [False, True, False, True, False, True, False, True, False, True, False, True],
        5: [False, True, False, True],
    },
    5: {
        1: [False, True, True, True, False, False, True, False, False, True, True, False],
        2: [True, False, True, False, True, True, True, False, False, False, True, False, False, True, False, True, False, True, False, True, False, True, True, False, True, True, False, True],
        3: [True, True, False, False, True, True, False, False, False, False, False, True, False, False, True, False, False, True, True, False, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True, False, True],
        4: [False, True, False, True, False, True, False, True, False, True, False, True],
        5: [False, True, False, True],
    },
}

# Points par thème R482
POINTS_THEME = {1: 12, 2: 28, 3: 44, 4: 12, 5: 4}
NB_QUESTIONS = {1: 12, 2: 28, 3: 44, 4: 12, 5: 4}

for num_grille, themes in GRILLES.items():
    grille = GrilleTheorie(famille="R482", numero=num_grille, annee=2024)
    db.add(grille)
    db.flush()

    for num_theme, reponses in themes.items():
        nb_q = NB_QUESTIONS[num_theme]
        pts_total = POINTS_THEME[num_theme]
        pts_par_question = pts_total / nb_q

        for i, rep in enumerate(reponses):
            r = ReponseGrille(
                grille_id=grille.id,
                theme=num_theme,
                numero_question=i + 1,
                reponse_correcte=rep,
                points=pts_par_question
            )
            db.add(r)

    print(f"Grille R482 n°{num_grille} encodée !")

db.commit()
db.close()
print("Toutes les grilles R482 sont en base !")