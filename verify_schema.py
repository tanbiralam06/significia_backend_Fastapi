from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.database.base import Base
from app.models import *

try:
    for table in Base.metadata.sorted_tables:
        print(CreateTable(table).compile(dialect=postgresql.dialect()))
    print("Schema verification passed!")
except Exception as e:
    print(f"Schema verification failed: {e}")
