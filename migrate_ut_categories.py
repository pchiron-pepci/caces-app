"""Migration : correction ut_pratique pour R482/A (1.5) et R482/G (1.2)."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non definie")

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    res_a = conn.execute(text("""
        UPDATE categories SET ut_pratique = 1.5
        WHERE code = 'A'
          AND famille_id = (SELECT id FROM familles WHERE code = 'R482')
    """))
    res_g = conn.execute(text("""
        UPDATE categories SET ut_pratique = 1.2
        WHERE code = 'G'
          AND famille_id = (SELECT id FROM familles WHERE code = 'R482')
    """))
    conn.commit()
    print(f"R482/A : {res_a.rowcount} ligne(s) mise(s) a jour -> ut_pratique = 1.5")
    print(f"R482/G : {res_g.rowcount} ligne(s) mise(s) a jour -> ut_pratique = 1.2")
