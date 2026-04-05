import os
from sqlalchemy import create_engine, text

# Get DATABASE_URL or use a default if it's not set
# DATABASE_URL=postgresql+psycopg://significia:significia@localhost:5432/significia
db_url = "postgresql+psycopg://significia:significia@localhost:5432/significia"

engine = create_engine(db_url)

with engine.connect() as conn:
    try:
        # Rename column in significia_core.clients
        conn.execute(text("ALTER TABLE significia_core.clients RENAME COLUMN declaration_date TO agreement_date;"))
        conn.commit()
        print("Successfully renamed declaration_date to agreement_date in significia_core.clients")
    except Exception as e:
        print(f"Error during migration: {e}")
