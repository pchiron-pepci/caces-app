from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    for row in result:
        print(row[0])