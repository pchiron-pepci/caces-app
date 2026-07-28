"""Migration idempotente : UT par engin sur R.482 categorie A.

La cat A se deroule sur 2 engins successifs (PH = engin N1, puis MB/CH/CP =
engin N2) = 2 prises de poste. La saisie pratique affiche donc 1 chrono PAR
engin, dont la duree vient de GrillePratique.ut :
    PH          -> 1.0 UT = 1 h    (seuil d'echec 70 min)
    MB/CH/CP    -> 0.5 UT = 30 min (seuil d'echec 35 min)
Total inchange : 1.0 + 0.5 = 1.5 UT = 1 h 30.

POURQUOI CE SCRIPT ET PAS init_grille_pratique_r482a.py :
le seed SUPPRIME puis RECREE les grilles. Sur une base qui porte deja des
saisies pratiques, la suppression est refusee par la contrainte de cle
etrangere saisie_item_note_item_id_fkey (les notes saisies referencent les
items) -- et heureusement, sinon elle detruirait des evaluations reelles.
Ici on ne touche QUE la colonne ut : aucune grille, aucun theme, aucun item,
aucune saisie n'est supprime ni modifie.

Usage : python migrate_ut_cat_a_engins.py
"""
from sqlalchemy import text
from app.database import engine

ATTENDU = {"PH": 1.0, "MB": 0.5, "CH": 0.5, "CP": 0.5}


def run():
    with engine.begin() as conn:
        lignes = conn.execute(text(
            "SELECT id, variante, ut FROM grille_pratique "
            "WHERE recommandation = 'R.482' AND categorie = 'A' AND type = 'base' "
            "ORDER BY ordre"
        )).fetchall()

        if not lignes:
            print("ATTENTION : aucune grille base R.482 cat A trouvee. "
                  "Rien a migrer (base non initialisee ?).")
            return

        print("Avant :")
        for _id, variante, ut in lignes:
            print("   id=%-5s %-4s ut=%s" % (_id, variante, ut))

        modifs = 0
        inconnues = []
        for _id, variante, ut in lignes:
            cible = ATTENDU.get(variante)
            if cible is None:
                inconnues.append((_id, variante))
                continue
            if ut is not None and abs(float(ut) - cible) < 1e-9:
                continue
            conn.execute(
                text("UPDATE grille_pratique SET ut = :ut WHERE id = :id"),
                {"ut": cible, "id": _id},
            )
            modifs += 1

        for _id, variante in inconnues:
            print("   ignoree : variante inattendue %r (id=%s) -- non modifiee"
                  % (variante, _id))

        apres = conn.execute(text(
            "SELECT variante, ut FROM grille_pratique "
            "WHERE recommandation = 'R.482' AND categorie = 'A' AND type = 'base' "
            "ORDER BY ordre"
        )).fetchall()

        print("Apres :")
        for variante, ut in apres:
            rang = "engin N1" if variante == "PH" else "engin N2"
            chrono = float(ut) * 60 if ut else 0
            seuil = float(ut) * 70 if ut else 0
            print("   %-4s %-9s ut=%.1f -> chrono %2d min, seuil d'echec %2d min"
                  % (variante, rang, float(ut or 0), chrono, seuil))

    if modifs:
        print("OK : %d grille(s) mise(s) a jour." % modifs)
    else:
        print("OK : rien a faire, les UT etaient deja correctes (idempotent).")


if __name__ == "__main__":
    run()
