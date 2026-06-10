"""
Diagnostic + correction du flag incluse sur option_categorie pour R482 (et toutes familles).
Affiche l'etat actuel, compare a la cible, puis propose le SQL de correction.
LECTURE SEULE — n'applique rien. Le SQL est juste affiche.
Lancer avec DATABASE_URL pointe vers la prod Render.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
SEP = "-" * 70

# Etat cible (source : init_options.py)
CIBLE = {
    ("R482", "A",   "PE"):  True,
    ("R482", "A",   "TEL"): False,
    ("R482", "B1",  "PE"):  False,
    ("R482", "B1",  "TEL"): False,
    ("R482", "B2",  "TEL"): True,
    ("R482", "C1",  "PE"):  False,
    ("R482", "C2",  "PE"):  False,
    ("R482", "C3",  "PE"):  False,
    ("R482", "D",   "PE"):  False,
    ("R482", "D",   "TEL"): False,
    ("R482", "E",   "PE"):  False,
    ("R482", "G",   "PE"):  False,
    ("R482", "G",   "TEL"): True,
    ("R482", "H",   "TEL"): False,
}

with engine.connect() as c:

    print(SEP)
    print("ETAT PROD — option_categorie R482 (toutes lignes)")
    print(SEP)
    rows = c.execute(text("""
        SELECT famille, categorie, code_option, incluse
          FROM option_categorie
         WHERE famille = 'R482'
         ORDER BY categorie, code_option
    """)).fetchall()

    ecarts = []
    for r in rows:
        fam, cat, opt, incluse_prod = r
        incluse_cible = CIBLE.get((fam, cat, opt))
        prod_label  = "INCLUSE"    if incluse_prod  else "facultative"
        cible_label = "INCLUSE"    if incluse_cible else "facultative"
        ok = (incluse_prod == incluse_cible)
        flag = "OK" if ok else "!!! ECART"
        print(f"  {fam}/{cat:4s}  {opt:4s}  prod={prod_label:12s}  cible={cible_label:12s}  {flag}")
        if not ok:
            ecarts.append((fam, cat, opt, incluse_cible))

    print()
    if not ecarts:
        print("Aucun ecart — flags R482 corrects en prod.")
    else:
        print(f"{len(ecarts)} ecart(s) detecte(s).")
        print()
        print(SEP)
        print("SQL DE CORRECTION (a copier/coller et executer sur prod)")
        print(SEP)
        print()
        # Regrouper par valeur cible
        a_false = [(f, cat, opt) for f, cat, opt, cible in ecarts if not cible]
        a_true  = [(f, cat, opt) for f, cat, opt, cible in ecarts if cible]

        if a_false:
            conds = " OR\n    ".join(
                f"(famille='{f}' AND categorie='{cat}' AND code_option='{opt}')"
                for f, cat, opt in a_false
            )
            print(f"-- Mettre incluse=FALSE sur {len(a_false)} ligne(s) erronee(s)")
            print(f"UPDATE option_categorie")
            print(f"SET incluse = FALSE")
            print(f"WHERE {conds};")
            print()

        if a_true:
            conds = " OR\n    ".join(
                f"(famille='{f}' AND categorie='{cat}' AND code_option='{opt}')"
                for f, cat, opt in a_true
            )
            print(f"-- Mettre incluse=TRUE sur {len(a_true)} ligne(s) erronee(s)")
            print(f"UPDATE option_categorie")
            print(f"SET incluse = TRUE")
            print(f"WHERE {conds};")
            print()

    # Verification globale : lignes incluse=True hors R482 pour info
    print(SEP)
    print("INFO — toutes les options incluse=TRUE en prod (toutes familles)")
    print(SEP)
    all_incluse = c.execute(text("""
        SELECT famille, categorie, code_option
          FROM option_categorie
         WHERE incluse = TRUE
         ORDER BY famille, categorie, code_option
    """)).fetchall()
    for r in all_incluse:
        print(f"  {r[0]}/{r[1]:4s}  {r[2]}")
    if not all_incluse:
        print("  Aucune ligne incluse=TRUE en prod.")

    print()
    print(SEP)
    print("FIN — aucune ecriture effectuee.")
    print(SEP)
