import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("DATABASE_URL non definie.")
    exit(1)

url = urlparse(DATABASE_URL)
conn = psycopg2.connect(
    dbname=url.path.lstrip("/"),
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port or 5432,
    sslmode="require"
)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS attestations_neutralite (
        id SERIAL PRIMARY KEY,
        jour_test_id INTEGER NOT NULL,
        stagiaire_id INTEGER NOT NULL,
        verificateur_identite VARCHAR(200),
        horodatage_verification TIMESTAMP,
        signature_base64 TEXT,
        horodatage TIMESTAMP,
        ip_address VARCHAR(50),
        CONSTRAINT uq_attestation_jour_stagiaire UNIQUE(jour_test_id, stagiaire_id)
    )
""")
conn.commit()
cur.close()
conn.close()
print("Migration attestations_neutralite OK.")
