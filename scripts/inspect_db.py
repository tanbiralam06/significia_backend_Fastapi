from sqlalchemy import create_engine, inspect

db_url = "postgresql+psycopg://significia:significia@localhost:5432/significia"
engine = create_engine(db_url)
inspector = inspect(engine)

print(f"Schemas: {inspector.get_schema_names()}")
for schema in inspector.get_schema_names():
    if not schema.startswith("pg_") and schema != "information_schema":
        print(f"Tables in {schema}: {inspector.get_table_names(schema=schema)}")
