import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from app.core.timezone import get_now_ist
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.auth_schema import UserRegisterRequest, UserLoginRequest, TokenResponse
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.core.jwt import create_access_token, create_refresh_token
from app.core.config import settings

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.tenant_repo = TenantRepository()

    def register_user(self, db: Session, request: UserRegisterRequest) -> User:
        # Check if email exists
        if self.user_repo.get_by_email(db, request.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create Tenant
        tenant = self.tenant_repo.create(
            db=db, 
            name=request.company_name, 
            subdomain=request.subdomain
        )

        # Create User
        user = User(
            tenant_id=tenant.id,
            email=request.email,
            email_normalized=request.email.lower(),
            password_hash=get_password_hash(request.password),
            role="owner",
            status="active"
        )
        created_user = self.user_repo.create(db, user)
        db.commit()
        db.refresh(created_user)
        return created_user

    def authenticate_user(self, db: Session, request: UserLoginRequest, request_ip: str, user_agent: str) -> TokenResponse:
        user = self.user_repo.get_by_email(db, request.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # 1. Check Account Lockout (15-min lockout after 5 failed attempts)
        now = get_now_ist()
        if user.locked_until and user.locked_until > now:
            wait_time = round((user.locked_until - now).total_seconds() / 60)
            raise HTTPException(
                status_code=423, 
                detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {wait_time} minutes."
            )
            
        if not user.password_hash:
            # This is likely an IA staff/owner who should use their specific portal
            raise HTTPException(
                status_code=401, 
                detail="This account is managed via a private portal. Please log in through your company's subdomain."
            )

        # 2. Verify Password and handle failures
        if not verify_password(request.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = get_now_ist() + timedelta(minutes=15)
                self.user_repo.update(db, user)
                raise HTTPException(
                    status_code=423, 
                    detail="Account locked for 15 minutes due to 5 failed attempts."
                )
            self.user_repo.update(db, user)
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        if user.status != "active":
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Increment session version (Single Device Login logic)
        user.refresh_token_version += 1
        
        # Generate tokens with the new version
        access_token = create_access_token(
            subject=str(user.id), 
            tenant_id=str(user.tenant_id), 
            role=user.role,
            version=user.refresh_token_version
        )
        refresh_token = create_refresh_token(
            subject=str(user.id), 
            tenant_id=str(user.tenant_id),
            version=user.refresh_token_version
        )

        # 3. Successful Login Logic
        # Update last login info, refresh token, and reset failed attempts
        user.last_login_at = get_now_ist()
        user.last_login_ip = request_ip
        user.failed_login_attempts = 0
        user.locked_until = None
        user.refresh_token = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        self.user_repo.update(db, user)
        db.commit()
        db.refresh(user)

        tenant = self.tenant_repo.get_by_id(db, user.tenant_id)
        subdomain = tenant.subdomain if tenant else None

        return TokenResponse(
            access_token=access_token, 
            refresh_token=refresh_token,
            subdomain=subdomain,
            is_profile_completed=tenant.is_profile_completed if tenant else False
        )

    def refresh_access_token(self, db: Session, refresh_token: str) -> TokenResponse:
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        user = db.query(User).filter(User.refresh_token == rt_hash).first()
        
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        # Verify session version
        try:
            from app.core.jwt import decode_token
            payload = decode_token(refresh_token)
            token_version = payload.get("version")
            if token_version != user.refresh_token_version:
                raise HTTPException(status_code=401, detail="Session invalidated. Please log in again.")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid session token")

        new_access_token = create_access_token(
            subject=str(user.id), 
            tenant_id=str(user.tenant_id), 
            role=user.role,
            version=user.refresh_token_version
        )
        
        tenant = self.tenant_repo.get_by_id(db, user.tenant_id)
        subdomain = tenant.subdomain if tenant else None

        return TokenResponse(
            access_token=new_access_token, 
            refresh_token=refresh_token,
            subdomain=subdomain,
            is_profile_completed=tenant.is_profile_completed if tenant else False
        )
