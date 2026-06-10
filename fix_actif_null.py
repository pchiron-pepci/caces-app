"""
Correction : met actif=TRUE sur toutes les categories dont actif IS NULL.
Affiche d'abord les lignes concernees, puis applique le UPDATE.
Lancer avec DATABASE_URL pointe vers la prod Render.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
SEP = "-" * 60

with engine.connect() as conn:

    # 1. Audit : toutes les categories avec actif IS NULL
    rows = conn.execute(text("""
        SELECT c.id, f.code AS famille, c.code, c.libelle, c.pepci_habilite, c.est_option
          FROM categories c
          JOIN familles f ON f.id = c.famille_id
         WHERE c.actif IS NULL
         ORDER BY f.code, c.code
    """)).fetchall()

    print(SEP)
    print(f"Categories avec actif IS NULL : {len(rows)} ligne(s)")
    print(SEP)
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  pepci_habilite={r[4]}  est_option={r[5]}  libelle={r[3]}")

    if not rows:
        print("  Aucune — rien a faire.")
    else:
        # 2. SQL qui sera execute
        print()
        print("SQL applique :")
        print("  UPDATE categories SET actif = TRUE WHERE actif IS NULL;")
        print()

        # 3. Correction
        n = conn.execute(text("UPDATE categories SET actif = TRUE WHERE actif IS NULL")).rowcount
        conn.commit()
        print(f"OK — {n} categorie(s) mises a jour (actif = TRUE).")

    print()
    print(SEP)
    print("FIN.")
    print(SEP)
