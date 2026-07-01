"""Corrige le libelle de la categorie G en base (init_data ne touche pas l'existant)."""
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./caces.db"))
with engine.begin() as cx:
    r = cx.execute(text(
        "UPDATE categories SET libelle = :lib WHERE code = 'G' "
        "AND famille_id = (SELECT id FROM familles WHERE code = 'R482')"
    ), {"lib": "Conduite des engins hors production"})
    print("[OK] libelle G mis a jour (%s ligne(s))" % r.rowcount)
