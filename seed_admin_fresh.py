import os
import uuid
import secrets
import getpass
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.tenant import Tenant
from app.models.user import User
from app.models.staff_profile import StaffProfile
from app.database.base import Base
import app.models # Ensure all models are registered in Base
from app.core.security import get_password_hash

# Use Environment Variable for Database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback for local development if not set
    DATABASE_URL = "postgresql+psycopg://significia:significia@localhost:5432/significia"

def create_super_admin(db, email, password, full_name, phone_number, designation, tenant_id):
    """Helper to create a super admin and their staff profile."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email,
            email_normalized=email.lower(),
            password_hash=get_password_hash(password),
            role="super_admin",
            status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created Super Admin User: {email}")
    else:
        print(f"Super Admin User {email} already exists.")

    profile = db.query(StaffProfile).filter(StaffProfile.user_id == user.id).first()
    if not profile:
        profile = StaffProfile(
            user_id=user.id,
            full_name=full_name,
            phone_number=phone_number,
            designation=designation,
            address="Significia Headquarters"
        )
        db.add(profile)
        db.commit()
        print(f"Created Staff Profile for: {full_name}")
    else:
        print(f"Staff Profile already exists for: {full_name}")

def seed():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    engine = create_engine(DATABASE_URL)
    
    # 0. Sync Schema
    print("Synchronizing database schema...")
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. Create Master Tenant
        tenant = db.query(Tenant).filter(Tenant.subdomain == "master").first()
        if not tenant:
            tenant = Tenant(
                id=uuid.uuid4(),
                name="Significia Core",
                subdomain="master",
                is_active=True
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"Created Master Tenant: {tenant.id}")

        # 2. Create Default Hardcoded Super Admin
        print("\n--- Step 1: Creating Default Super Admin ---")
        create_super_admin(
            db, 
            email="alamtanbir328@gmail.com",
            password="T@nbir#2026",
            full_name="Tanbir Alam",
            phone_number="8927611404",
            designation="System Admin",
            tenant_id=tenant.id
        )

        # 3. Create Additional Super Admins Interactively
        print("\n--- Step 2: Creating Additional Super Admins (2 remaining) ---")
        for i in range(1, 3):
            print(f"\nRegistering Super Admin #{i+1}")
            email = input("Email: ").strip()
            if not email:
                print("Skipping...")
                continue
            
            name = input("Full Name: ").strip()
            password = getpass.getpass("Password: ")
            confirm_password = getpass.getpass("Confirm Password: ")
            
            if password != confirm_password:
                print("Error: Passwords do not match. Skipping this admin.")
                continue
            
            create_super_admin(
                db,
                email=email,
                password=password,
                full_name=name,
                phone_number="0000000000", # Placeholder
                designation="Super Admin",
                tenant_id=tenant.id
            )

        print("\nSeeding completed successfully!")

    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
