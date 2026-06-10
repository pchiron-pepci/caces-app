"""
Verification FK avant migration R483/R487/R490.
Affiche le detail des enregistrements references dans les tables metier
pour les categories concernees par la migration.
AUCUNE ecriture — lecture seule.
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./caces.db")
engine = create_engine(DATABASE_URL)

SEPARATOR = "-" * 72

def run(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).fetchall()

with engine.connect() as conn:

    print(SEPARATOR)
    print("CHECK FK — R483 cats 1/2/3/4 (ex-Grues a tour, mal rangees)")
    print(SEPARATOR)

    # Habilitations sur R483/1/2/3/4
    rows = run(conn, """
        SELECT ht.id, ht.famille, ht.categorie, ht.date_integration,
               t.nom, t.prenom, t.actif
          FROM habilitations_testeurs ht
          JOIN testeurs t ON t.id = ht.testeur_id
         WHERE ht.famille = 'R483' AND ht.categorie IN ('1','2','3','4')
         ORDER BY t.nom, ht.categorie
    """)
    print(f"\nhabilitations_testeurs R483 cats 1/2/3/4 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  date={r[3]}  testeur: {r[4]} {r[5]}  actif={r[6]}")

    # Sessions epreuves sur R483/1/2/3/4
    rows = run(conn, """
        SELECT se.id, se.famille, se.categorie, se.obtenue,
               s.nom AS stag_nom, s.prenom AS stag_prenom,
               sess.id AS session_id, sess.reference
          FROM session_epreuves se
          JOIN stagiaires s ON s.id = se.stagiaire_id
          JOIN sessions sess ON sess.id = se.session_id
         WHERE se.famille = 'R483' AND se.categorie IN ('1','2','3','4')
         ORDER BY sess.id, s.nom
    """)
    print(f"\nsession_epreuves R483 cats 1/2/3/4 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  se.id={r[0]}  {r[1]}/{r[2]}  obtenue={r[3]}  stagiaire: {r[4]} {r[5]}  session={r[6]} ref={r[7]}")

    # CACES obtenus sur R483/1/2/3/4
    rows = run(conn, """
        SELECT co.id, co.famille, co.categorie, co.statut,
               s.nom, s.prenom
          FROM caces_obtenus co
          JOIN stagiaires s ON s.id = co.stagiaire_id
         WHERE co.famille = 'R483' AND co.categorie IN ('1','2','3','4')
         ORDER BY s.nom
    """)
    print(f"\ncaces_obtenus R483 cats 1/2/3/4 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  statut={r[3]}  stagiaire: {r[4]} {r[5]}")

    print()
    print(SEPARATOR)
    print("CHECK FK — R487 cats A/B (Grues mobiles, a migrer vers R483)")
    print(SEPARATOR)

    # Habilitations sur R487/A/B
    rows = run(conn, """
        SELECT ht.id, ht.famille, ht.categorie, ht.date_integration,
               t.nom, t.prenom, t.actif
          FROM habilitations_testeurs ht
          JOIN testeurs t ON t.id = ht.testeur_id
         WHERE ht.famille = 'R487' AND ht.categorie IN ('A','B')
         ORDER BY t.nom, ht.categorie
    """)
    print(f"\nhabilitations_testeurs R487 A/B : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  date={r[3]}  testeur: {r[4]} {r[5]}  actif={r[6]}")

    # Sessions utilisant R487 (toutes cats)
    rows = run(conn, """
        SELECT id, reference, statut, famille
          FROM sessions
         WHERE famille = 'R487'
         ORDER BY id
    """)
    print(f"\nsessions famille R487 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  session_id={r[0]}  ref={r[1]}  statut={r[2]}  famille={r[3]}")

    # Sessions epreuves sur R487/A/B
    rows = run(conn, """
        SELECT se.id, se.famille, se.categorie, se.obtenue,
               s.nom, s.prenom,
               sess.id AS session_id, sess.reference
          FROM session_epreuves se
          JOIN stagiaires s ON s.id = se.stagiaire_id
          JOIN sessions sess ON sess.id = se.session_id
         WHERE se.famille = 'R487' AND se.categorie IN ('A','B')
         ORDER BY sess.id, s.nom
    """)
    print(f"\nsession_epreuves R487 A/B : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  se.id={r[0]}  {r[1]}/{r[2]}  obtenue={r[3]}  stagiaire: {r[4]} {r[5]}  session={r[6]} ref={r[7]}")

    # CACES obtenus sur R487/A/B
    rows = run(conn, """
        SELECT co.id, co.famille, co.categorie, co.statut,
               s.nom, s.prenom
          FROM caces_obtenus co
          JOIN stagiaires s ON s.id = co.stagiaire_id
         WHERE co.famille = 'R487' AND co.categorie IN ('A','B')
         ORDER BY s.nom
    """)
    print(f"\ncaces_obtenus R487 A/B : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  statut={r[3]}  stagiaire: {r[4]} {r[5]}")

    print()
    print(SEPARATOR)
    print("CHECK FK — R490 cats 2/3 (a supprimer)")
    print(SEPARATOR)

    # Habilitations sur R490/2/3
    rows = run(conn, """
        SELECT ht.id, ht.famille, ht.categorie, ht.date_integration,
               t.nom, t.prenom, t.actif
          FROM habilitations_testeurs ht
          JOIN testeurs t ON t.id = ht.testeur_id
         WHERE ht.famille = 'R490' AND ht.categorie IN ('2','3')
         ORDER BY t.nom, ht.categorie
    """)
    print(f"\nhabilitations_testeurs R490 cats 2/3 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  date={r[3]}  testeur: {r[4]} {r[5]}  actif={r[6]}")

    # Sessions epreuves sur R490/2/3
    rows = run(conn, """
        SELECT se.id, se.famille, se.categorie, se.obtenue,
               s.nom, s.prenom,
               sess.id AS session_id, sess.reference
          FROM session_epreuves se
          JOIN stagiaires s ON s.id = se.stagiaire_id
          JOIN sessions sess ON sess.id = se.session_id
         WHERE se.famille = 'R490' AND se.categorie IN ('2','3')
         ORDER BY sess.id, s.nom
    """)
    print(f"\nsession_epreuves R490 cats 2/3 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  se.id={r[0]}  {r[1]}/{r[2]}  obtenue={r[3]}  stagiaire: {r[4]} {r[5]}  session={r[6]} ref={r[7]}")

    # CACES obtenus sur R490/2/3
    rows = run(conn, """
        SELECT co.id, co.famille, co.categorie, co.statut,
               s.nom, s.prenom
          FROM caces_obtenus co
          JOIN stagiaires s ON s.id = co.stagiaire_id
         WHERE co.famille = 'R490' AND co.categorie IN ('2','3')
         ORDER BY s.nom
    """)
    print(f"\ncaces_obtenus R490 cats 2/3 : {len(rows)} ligne(s)")
    for r in rows:
        print(f"  id={r[0]}  {r[1]}/{r[2]}  statut={r[3]}  stagiaire: {r[4]} {r[5]}")

    print()
    print(SEPARATOR)
    print("FIN — aucune ecriture effectuee.")
    print(SEPARATOR)
