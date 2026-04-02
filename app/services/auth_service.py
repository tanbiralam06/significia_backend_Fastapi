import uuid
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from app.core.timezone import get_now_ist
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.auth_schema import UserRegisterRequest, UserLoginRequest, TokenResponse
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.session_repository import SessionRepository
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.core.jwt import create_access_token, create_refresh_token
from app.core.config import settings

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.tenant_repo = TenantRepository()
        self.session_repo = SessionRepository()

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
        return self.user_repo.create(db, user)

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

        # Generate tokens
        access_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        refresh_token = create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id))

        # Hash refresh token for storage
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = get_now_ist() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Store Refresh Token
        self.session_repo.create_refresh_token(db, user.id, user.tenant_id, rt_hash, expires_at)
        
        # Store Session (using access token hash for session linking)
        access_hash = hashlib.sha256(access_token.encode()).hexdigest()
        at_expires = get_now_ist() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.session_repo.create_session(db, user.id, user.tenant_id, access_hash, device=None, ip_address=request_ip, expires_at=at_expires)

        # 3. Successful Login Logic
        # Update last login info and reset failed attempts
        user.last_login_at = get_now_ist()
        user.last_login_ip = request_ip
        user.failed_login_attempts = 0
        user.locked_until = None
        self.user_repo.update(db, user)

        tenant = self.tenant_repo.get_by_id(db, user.tenant_id)
        subdomain = tenant.subdomain if tenant else None

        return TokenResponse(
            access_token=access_token, 
            refresh_token=refresh_token,
            subdomain=subdomain
        )

    def refresh_access_token(self, db: Session, refresh_token: str) -> TokenResponse:
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored_token = self.session_repo.get_refresh_token(db, rt_hash)
        
        if not stored_token or stored_token.expires_at < get_now_ist():
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user = self.user_repo.get_by_id(db, stored_token.user_id)
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="User account is disabled or missing")

        new_access_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        new_access_hash = hashlib.sha256(new_access_token.encode()).hexdigest()
        at_expires = get_now_ist() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        self.session_repo.create_session(db, user.id, user.tenant_id, new_access_hash, device=None, ip_address=None, expires_at=at_expires)
        
        tenant = self.tenant_repo.get_by_id(db, user.tenant_id)
        subdomain = tenant.subdomain if tenant else None

        return TokenResponse(
            access_token=new_access_token, 
            refresh_token=refresh_token,
            subdomain=subdomain
        )
