import os
import sys

# Ensure the app module is in the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import get_password_hash
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository

def create_superuser(email: str, password: str):
    db = SessionLocal()
    user_repo = UserRepository()
    tenant_repo = TenantRepository()
    
    try:
        # 1. Ensure Global Master Tenant exists
        tenant_name = "Significia Master"
        tenant_subdomain = "master"
        
        tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_subdomain).first()
        if not tenant:
            print(f"[*] Creating '{tenant_name}' global tenant in Master DB...")
            tenant = tenant_repo.create(db, name=tenant_name, subdomain=tenant_subdomain)
            print(f"[+] Tenant created with ID: {tenant.id}")
        else:
            print(f"[*] Found existing global tenant: {tenant.name} ({tenant.subdomain})")

        # 2. Create or Update Super User
        user = user_repo.get_by_email(db, email)
        if user:
            print(f"[*] User {email} already exists. Updating role and password...")
            user.password_hash = get_password_hash(password)
            user.role = "super_admin"
            user.status = "active"
            user.email_verified = True
            db.commit()
            print(f"[+] User updated successfully.")
        else:
            print(f"[*] Creating new super user {email}...")
            user = User(
                tenant_id=tenant.id,
                email=email,
                email_normalized=email.lower(),
                password_hash=get_password_hash(password),
                role="super_admin",
                status="active",
                email_verified=True
            )
            user_repo.create(db, user)
            print(f"[+] Super user created successfully.")

        print("\n[!] Super User Details:")
        print(f"    - Email: {email}")
        print(f"    - Tenant: {tenant.name} (Global)")
        print(f"    - Role: {user.role}")
        print(f"    - Status: {user.status}")

    except Exception as e:
        print(f"[!] Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a Significia Super User")
    parser.add_argument("--email", help="Email for the super user", default="alamtanbir@gmail.com")
    parser.add_argument("--password", help="Password for the super user", default="T@nbir#2026")
    
    args = parser.parse_args()
    
    print(f"--- Starting Super User Creation for {args.email} ---")
    create_superuser(args.email, args.password)
    print("--- Finished ---")
