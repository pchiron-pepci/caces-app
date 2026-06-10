"""
Diagnostic R487 invisible dans la cartographie admin.
Lecture seule — aucune ecriture.
Lancer avec DATABASE_URL pointe vers la prod Render.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
SEP = "-" * 60

with engine.connect() as c:

    # 1. Famille R487 — toutes colonnes
    print(SEP)
    print("1. Famille R487 (toutes colonnes)")
    print(SEP)
    row = c.execute(text("SELECT * FROM familles WHERE code = 'R487'")).fetchone()
    if row:
        keys = c.execute(text("SELECT * FROM familles WHERE code = 'R487'")).keys()
        for k, v in zip(keys, row):
            print(f"  {k} = {v!r}")
    else:
        print("  INTROUVABLE")

    # 2. Categories R487/1/2/3 — colonnes cles
    print()
    print(SEP)
    print("2. Categories R487 (id, code, famille_id, pepci_habilite, actif, est_option)")
    print(SEP)
    rows = c.execute(text("""
        SELECT c.id, c.code, c.famille_id, c.pepci_habilite, c.actif, c.est_option
          FROM categories c
          JOIN familles f ON f.id = c.famille_id
         WHERE f.code = 'R487'
         ORDER BY c.code
    """)).fetchall()
    if rows:
        for r in rows:
            print(f"  id={r[0]}  code={r[1]}  famille_id={r[2]}  pepci_habilite={r[3]}  actif={r[4]}  est_option={r[5]}")
    else:
        print("  Aucune categorie trouvee pour R487")

    # 3. Requete exacte "non habilitees" (page /admin, main.py:554)
    print()
    print(SEP)
    print("3. Requete exacte section non-habilitees (main.py route GET /admin)")
    print(SEP)
    print("""
  -- Route GET /admin, main.py :
  familles       = db.query(Famille).filter(Famille.actif == True).all()
  categories_raw = db.query(Categorie).filter(Categorie.actif == True).all()

  -- Puis pour chaque categorie dans categories_raw, la famille est chargee :
  f = db.query(Famille).filter(Famille.id == c.famille_id).first()
  c.famille_code = f.code if f else "?"

  -- Seul filtre sur Categorie : actif == True (pas de filtre pepci_habilite)
  -- Seul filtre sur Famille  : actif == True
    """)

    # Verification croisee : combien de categories actif=True vs actif=NULL/False pour R487
    print(SEP)
    print("4. Comptage actif par valeur pour les categories R487")
    print(SEP)
    for label, sql in [
        ("actif IS TRUE",  "SELECT COUNT(*) FROM categories c JOIN familles f ON f.id=c.famille_id WHERE f.code='R487' AND c.actif IS TRUE"),
        ("actif IS FALSE", "SELECT COUNT(*) FROM categories c JOIN familles f ON f.id=c.famille_id WHERE f.code='R487' AND c.actif IS FALSE"),
        ("actif IS NULL",  "SELECT COUNT(*) FROM categories c JOIN familles f ON f.id=c.famille_id WHERE f.code='R487' AND c.actif IS NULL"),
    ]:
        n = c.execute(text(sql)).scalar()
        print(f"  {label} : {n}")

    print()
    print(SEP)
    print("FIN — aucune ecriture effectuee.")
    print(SEP)
