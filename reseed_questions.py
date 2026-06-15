"""
reseed_questions.py
Réinsère uniquement les questions (reponses_grilles) R482 sans toucher aux grilles ni aux autres tables.

Prérequis :
  - La table reponses_grilles doit être vide (le script refuse sinon).
  - Les grilles_theorie R482 (numeros 1-5) doivent exister.

Commande Render Shell :
  python reseed_questions.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.grille_theorie import GrilleTheorie, ReponseGrille
from init_questions_r482 import GRILLES_R482, POINTS_THEME, get_image_url


def run():
    db = SessionLocal()
    try:
        count = db.query(ReponseGrille).count()
        if count > 0:
            print(f"❌ La table reponses_grilles contient déjà {count} enregistrement(s). Abandon.")
            print("   Videz d'abord la table si vous voulez réinsérer (DELETE FROM reponses_grilles;).")
            return

        total = 0
        for grille_num, themes in GRILLES_R482.items():
            grille = db.query(GrilleTheorie).filter(
                GrilleTheorie.famille == "R482",
                GrilleTheorie.numero == grille_num
            ).first()
            if not grille:
                print(f"❌ Grille R482 n°{grille_num} introuvable dans grilles_theorie. Abandon.")
                db.rollback()
                return

            nb_q = 0
            for theme_num, questions in themes.items():
                for (q_num, texte, reponse) in questions:
                    db.add(ReponseGrille(
                        grille_id=grille.id,
                        theme=theme_num,
                        numero_question=q_num,
                        reponse_correcte=reponse,
                        points=POINTS_THEME[theme_num],
                        texte_question=texte,
                        image_url=get_image_url(grille_num, theme_num, q_num),
                    ))
                    nb_q += 1

            db.commit()
            total += nb_q
            print(f"✅ Grille {grille_num} (id={grille.id}) — {nb_q} questions insérées")

        print(f"\n✅ Total : {total} questions insérées\n")

        print("Vérification :")
        for grille_num in range(1, 6):
            g = db.query(GrilleTheorie).filter(
                GrilleTheorie.famille == "R482",
                GrilleTheorie.numero == grille_num
            ).first()
            counts = {t: db.query(ReponseGrille).filter(
                ReponseGrille.grille_id == g.id,
                ReponseGrille.theme == t
            ).count() for t in range(1, 6)}
            total_g = sum(counts.values())
            ok = "✅" if total_g == 100 else "❌"
            print(f"  {ok} Grille {grille_num} : T1={counts[1]} T2={counts[2]} T3={counts[3]} T4={counts[4]} T5={counts[5]} → {total_g}/100")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
