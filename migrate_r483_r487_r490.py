"""
Migration R483/R487/R490 — correction des familles et categories.

R483 : libelle -> "Grues mobiles", cats parasites 1/2/3/4 supprimees,
       cats A/B recuperees depuis R487 (move famille_id).
R487 : libelle -> "Grues a tour", cats A/B parties vers R483,
       nouvelles cats 1/2/3 creees avec UT corrects.
R490 : cats 2/3 et OPT-TEL supprimees, cat 1 conservee.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:

    # --- Recuperer les famille_id ---
    def fid(code):
        row = conn.execute(text("SELECT id FROM familles WHERE code = :c"), {"c": code}).fetchone()
        if not row:
            raise RuntimeError(f"Famille {code} introuvable")
        return row[0]

    fid_483 = fid("R483")
    fid_487 = fid("R487")
    fid_490 = fid("R490")

    # --- Swap libelles ---
    conn.execute(text("UPDATE familles SET libelle = 'Grues mobiles' WHERE id = :id"), {"id": fid_483})
    conn.execute(text("UPDATE familles SET libelle = 'Grues a tour'  WHERE id = :id"), {"id": fid_487})
    conn.commit()
    print("OK — libelles famille swapes (R483=Grues mobiles, R487=Grues a tour)")

    # --- R483 : deplacer A/B depuis R487 ---
    n = conn.execute(text(
        "UPDATE categories SET famille_id = :f483 WHERE famille_id = :f487 AND code IN ('A','B')"
    ), {"f483": fid_483, "f487": fid_487}).rowcount
    conn.commit()
    print(f"OK — {n} categorie(s) A/B deplacees R487 -> R483")

    # --- R483 : supprimer cats parasites 1/2/3/4 ---
    n = conn.execute(text(
        "DELETE FROM categories WHERE famille_id = :fid AND code IN ('1','2','3','4')"
    ), {"fid": fid_483}).rowcount
    conn.commit()
    print(f"OK — {n} categorie(s) 1/2/3/4 supprimees sous R483")

    # --- R487 : creer cats 1/2/3 ---
    nouvelles = [
        ("1", "Grue a tour a montage par elements, fleche distributrice", 1.2),
        ("2", "Grue a tour a montage par elements, fleche relevable",     1.0),
        ("3", "Grue a tour a montage automatise",                          1.0),
    ]
    for code, libelle, ut in nouvelles:
        existing = conn.execute(text(
            "SELECT id FROM categories WHERE famille_id = :fid AND code = :c"
        ), {"fid": fid_487, "c": code}).fetchone()
        if not existing:
            conn.execute(text(
                "INSERT INTO categories (famille_id, code, libelle, ut_pratique, pepci_habilite, est_option)"
                " VALUES (:fid, :code, :libelle, :ut, :ph, :eo)"
            ), {"fid": fid_487, "code": code, "libelle": libelle, "ut": ut, "ph": False, "eo": False})
    conn.commit()
    print("OK — cats R487/1/2/3 creees")

    # --- R490 : supprimer cats 2/3 et OPT-TEL ---
    n = conn.execute(text(
        "DELETE FROM categories WHERE famille_id = :fid AND code IN ('2','3','OPT-TEL')"
    ), {"fid": fid_490}).rowcount
    conn.commit()
    print(f"OK — {n} categorie(s) 2/3/OPT-TEL supprimees sous R490")

    # --- Verification finale ---
    print()
    print("=== Etat final R483 ===")
    for r in conn.execute(text(
        "SELECT code, libelle, ut_pratique FROM categories WHERE famille_id = :fid ORDER BY code"
    ), {"fid": fid_483}):
        print(f"  {r[0]}  |  {r[1]}  |  ut={r[2]}")

    print("=== Etat final R487 ===")
    for r in conn.execute(text(
        "SELECT code, libelle, ut_pratique FROM categories WHERE famille_id = :fid ORDER BY code"
    ), {"fid": fid_487}):
        print(f"  {r[0]}  |  {r[1]}  |  ut={r[2]}")

    print("=== Etat final R490 ===")
    for r in conn.execute(text(
        "SELECT code, libelle, ut_pratique FROM categories WHERE famille_id = :fid ORDER BY code"
    ), {"fid": fid_490}):
        print(f"  {r[0]}  |  {r[1]}  |  ut={r[2]}")

    print()
    print("Migration terminee.")
