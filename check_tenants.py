import sys
import os
sys.path.insert(0, os.getcwd())

from app.database.session import SessionLocal
from app.models.tenant import Tenant

def check_tenants():
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        print("Subdomain | Name | Is Profile Completed")
        print("-" * 40)
        for t in tenants:
            print(f"{t.subdomain} | {t.name} | {t.is_profile_completed}")
    finally:
        db.close()

if __name__ == "__main__":
    check_tenants()
