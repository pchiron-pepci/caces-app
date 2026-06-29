"""
Diagnostic : pourquoi le séquencement affiche 2.5 UT au lieu de 3.0
pour un candidat avec A (PE incluse) + C1 (PE facultative) en R482.

Affiche :
  1. Les flags incluse R482 dans opt_incluse_set (source : option_categorie)
  2. Les jours pratiques R482 avec le contenu brut de options_planifiees
     + le calcul UT serveur simulé localement

Lecture seule. Lancer avec DATABASE_URL pointant vers la base voulue.
"""
import json
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)
SEP = "-" * 70

with engine.connect() as c:

    # 1. opt_incluse_set pour R482
    print(SEP)
    print("opt_incluse_set R482 (options avec incluse=TRUE en base)")
    print(SEP)
    rows = c.execute(text("""
        SELECT categorie, code_option, incluse
          FROM option_categorie
         WHERE famille = 'R482'
         ORDER BY categorie, code_option
    """)).fetchall()
    opt_incluse_set = set()
    for cat, opt, incluse in rows:
        flag = "INCLUSE" if incluse else "facultative"
        if incluse:
            opt_incluse_set.add((cat, opt))
        print(f"  R482/{cat:4s}  {opt:4s}  {flag}")
    print(f"\n  opt_incluse_set = {opt_incluse_set}")

    # 2. ut_par_cat R482
    ut_par_cat = {}
    for row in c.execute(text("""
        SELECT c.code, c.ut_pratique
          FROM categories c
          JOIN familles f ON f.id = c.famille_id
         WHERE f.code = 'R482'
    """)):
        ut_par_cat[row[0]] = float(row[1])

    # 3. Jours pratiques R482 avec leur options_planifiees
    print()
    print(SEP)
    print("Jours pratiques R482 — options_planifiees + calcul UT simulé")
    print(SEP)
    jours = c.execute(text("""
        SELECT j.id, j.date, s.reference
          FROM jours_test j
          JOIN sessions s ON s.id = j.session_id
          JOIN familles f ON f.code = s.famille
         WHERE j.type = 'pratique'
           AND s.famille = 'R482'
         ORDER BY j.date DESC
         LIMIT 10
    """)).fetchall()

    if not jours:
        print("  Aucun jour pratique R482 trouvé.")
    else:
        for jour_id, jour_date, ref in jours:
            print(f"\n  Jour #{jour_id}  {jour_date}  session={ref}")
            jtcs = c.execute(text("""
                SELECT jtc.id, jtc.stagiaire_id, jtc.categories, jtc.options_planifiees
                  FROM jour_test_candidats jtc
                 WHERE jtc.jour_test_id = :jid
                   AND jtc.actif = TRUE
            """), {"jid": jour_id}).fetchall()

            if not jtcs:
                print("    (aucun candidat actif)")
                continue

            total_ut = 0
            for jtc_id, stag_id, cats_str, opts_json in jtcs:
                cats = [c.strip() for c in (cats_str or "").split(",") if c.strip()]
                ut_cand = sum(ut_par_cat.get(cat, 1.0) for cat in cats)
                total_ut += ut_cand

                opts_parsed = {}
                if opts_json:
                    try:
                        opts_parsed = json.loads(opts_json)
                    except Exception:
                        pass

                ut_opts = 0
                for cat_code, opt_list in opts_parsed.items():
                    for opt_code in opt_list:
                        if (cat_code, opt_code) not in opt_incluse_set:
                            ut_opts += 0.5
                            total_ut += 0.5

                print(f"    candidat {stag_id}  cats={cats}  ut_base={ut_cand}")
                print(f"      options_planifiees (brut) : {opts_json!r}")
                print(f"      options parsées           : {opts_parsed}")
                if opts_parsed:
                    for cat_code, opt_list in opts_parsed.items():
                        for opt_code in opt_list:
                            incluse = (cat_code, opt_code) in opt_incluse_set
                            print(f"        {cat_code}/{opt_code} -> incluse={incluse} -> +{'0 (skip)' if incluse else '0.5'}")
                print(f"      ut_options={ut_opts}")

            print(f"  >>> total_ut calculé = {round(total_ut, 1)}")

    print()
    print(SEP)
    print("FIN — aucune écriture effectuée.")
    print(SEP)
