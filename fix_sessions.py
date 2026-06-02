from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("UPDATE sessions SET type='caces' WHERE type IS NULL"))
    conn.commit()
    print('OK!')