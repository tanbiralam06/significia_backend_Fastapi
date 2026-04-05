from sqlalchemy import create_engine, text

db_url = "postgresql+psycopg://significia:significia@localhost:5432/significia"
engine = create_engine(db_url)

with engine.connect() as conn:
    # Find all table schemas for table 'clients'
    query = text("SELECT table_schema FROM information_schema.tables WHERE table_name = 'clients'")
    result = conn.execute(query).fetchall()
    
    if result:
        print(f"Found 'clients' table in schema(s): {[r[0] for r in result]}")
    else:
        print("Table 'clients' not found in any schema.")
