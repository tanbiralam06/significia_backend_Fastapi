import os
import sys
import argparse

# Use print instead of loguru to avoid missing dependencies if they aren't installed globally.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserRegisterRequest
from app.repositories.user_repository import UserRepository

def parse_args():
    parser = argparse.ArgumentParser(description="Create a primary admin user.")
    parser.add_argument("--email", required=True, help="Admin Email")
    parser.add_argument("--password", required=True, help="Admin Password")
    parser.add_argument("--company", required=True, help="Admin Company/Tenant Name")
    parser.add_argument("--name", default="Admin", help="Admin Full Name")
    return parser.parse_args()

def main():
    args = parse_args()
    db = SessionLocal()
    try:
        print("[!] Initializing AuthService...")
        auth_service = AuthService()
        print("[!] Initializing UserRepository...")
        user_repo = UserRepository()

        print(f"[!] Executing UserRepository.get_by_email for {args.email} ...")
        existing_user = user_repo.get_by_email(db, args.email)
        print("[!] Email lookup returned")
        if existing_user:
            print(f"[-] User with email '{args.email}' already exists.")
            return

        print("[!] Constructing Registration Payload...")
        request_data = UserRegisterRequest(
            email=args.email,
            password=args.password,
            full_name=args.name,
            company_name=args.company
        )

        print(f"[*] Calling auth_service.register_user...")
        user = auth_service.register_user(db, request_data)
        
        print(f"[*] User object built! Triggering role override commit...")
        user.role = "owner"
        db.commit()

        print(f"[+] Successfully created admin user!")
        print(f"    - Email: {user.email}")
        print(f"    - Tenant ID: {user.tenant_id}")
        print(f"    - Role: {user.role}")

    except Exception as e:
        print(f"[!] Failed to create admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
