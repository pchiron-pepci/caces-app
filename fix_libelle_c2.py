"""Corrige le libelle de la categorie C2 en base (init_data ne touche pas l'existant)."""
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./caces.db"))
with engine.begin() as cx:
    r = cx.execute(text(
        "UPDATE categories SET libelle = :lib WHERE code = 'C2' "
        "AND famille_id = (SELECT id FROM familles WHERE code = 'R482')"
    ), {"lib": "Engins de reglage a deplacement alternatif"})
    print("[OK] libelle C2 mis a jour (%s ligne(s))" % r.rowcount)
