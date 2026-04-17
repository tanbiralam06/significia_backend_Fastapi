import os
import sys

# Add the backend directory to sys.path to allow imports from 'app'
sys.path.append(os.getcwd())

from sqlalchemy import update
from app.database.session import SessionLocal
from app.models.user import User

def migrate_analyst_roles():
    print("Starting role migration: analyst -> research_analyst...")
    db = SessionLocal()
    try:
        # Perform the update
        stmt = (
            update(User)
            .where(User.role == "analyst")
            .values(role="research_analyst")
        )
        result = db.execute(stmt)
        db.commit()
        print(f"Migration complete. Updated {result.rowcount} records.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_analyst_roles()
