import uuid
import uuid
import hashlib
from datetime import datetime, timedelta
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
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        if user.status != "active":
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Generate tokens
        access_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        refresh_token = create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id))

        # Hash refresh token for storage
        rt_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Store Refresh Token
        self.session_repo.create_refresh_token(db, user.id, user.tenant_id, rt_hash, expires_at)
        
        # Store Session (using access token hash for session linking)
        access_hash = hashlib.sha256(access_token.encode()).hexdigest()
        at_expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.session_repo.create_session(db, user.id, user.tenant_id, access_hash, device=None, ip_address=request_ip, expires_at=at_expires)

        # Update last login info
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = request_ip
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
        
        if not stored_token or stored_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user = self.user_repo.get_by_id(db, stored_token.user_id)
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="User account is disabled or missing")

        new_access_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        new_access_hash = hashlib.sha256(new_access_token.encode()).hexdigest()
        at_expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        self.session_repo.create_session(db, user.id, user.tenant_id, new_access_hash, device=None, ip_address=None, expires_at=at_expires)
        
        tenant = self.tenant_repo.get_by_id(db, user.tenant_id)
        subdomain = tenant.subdomain if tenant else None

        return TokenResponse(
            access_token=new_access_token, 
            refresh_token=refresh_token,
            subdomain=subdomain
        )
