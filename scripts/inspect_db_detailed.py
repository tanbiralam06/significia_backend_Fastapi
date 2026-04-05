from sqlalchemy import create_engine, inspect

db_url = "postgresql+psycopg://significia:significia@localhost:5432/significia"
engine = create_engine(db_url)
inspector = inspect(engine)

for schema in inspector.get_schema_names():
    if not schema.startswith("pg_") and schema != "information_schema":
        print(f"--- Schema: {schema} ---")
        tables = inspector.get_table_names(schema=schema)
        for table in tables:
            columns = [c["name"] for c in inspector.get_columns(table, schema=schema)]
            print(f"Table: {table}, Columns: {columns}")
