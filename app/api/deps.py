import uuid
import hashlib
import logging
from typing import Generator, List, Optional, Any
from datetime import datetime, timezone
from app.core.timezone import get_now_ist, to_ist as make_aware_ist

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.tenant import Tenant
from app.models.client import ClientProfile
from app.core.jwt import decode_token
from app.core.config import settings
from app.services.bridge_client import BridgeClient
from app.utils.encryption import decrypt_string

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str | None = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = UserRepository().get_by_id(db, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Inactive user")
    
    # ── Tenant Level Enforcement ────────────────────────────────────
    # Non-super_admins must belong to an active, non-expired tenant
    if user.role != "super_admin":
        tenant = user.tenant
        if not tenant:
            raise HTTPException(status_code=403, detail="User has no tenant assignment")
        if not tenant.is_active:
            raise HTTPException(status_code=403, detail="Your organization account is deactivated.")
        if tenant.plan_expiry_date and make_aware_ist(tenant.plan_expiry_date) < get_now_ist():
            raise HTTPException(status_code=403, detail="Your subscription plan has expired. Please renew to continue.")
             
    return user

def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Strict dependency for Super Admin routes.
    Ensures the user has the 'super_admin' role AND belongs to the 'master' tenant.
    """
    if current_user.role != "super_admin" or current_user.tenant.subdomain != "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access restricted to Super Admins only."
        )
    return current_user

def get_current_ia_owner(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency for IA Owner self-service routes (e.g. settings).
    Ensures the user is an 'owner' of their respective tenant.
    """
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Organization Owners."
        )
    return current_user

def require_profile_completed(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure the IA Master has completed their institutional profile.
    Blocks access to core features if the profile is incomplete.
    """
    if current_user.role == "owner" and not current_user.is_profile_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PROFILE_INCOMPLETE"
        )
    return current_user

def get_tenant_by_slug(
    x_tenant_slug: str | None = Header(None, alias="X-Tenant-Slug"),
    host: str | None = Header(None),
    x_api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> Tenant | None:
    tenant = None
    if x_api_key:
        hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
        api_key_obj = db.query(ApiKey).filter(ApiKey.hashed_key == hashed, ApiKey.is_active == True).first()
        if not api_key_obj:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        tenant = db.query(Tenant).filter(Tenant.id == api_key_obj.tenant_id).first()
    elif x_tenant_slug:
        tenant = db.query(Tenant).filter(Tenant.subdomain == x_tenant_slug).first()
    elif host:
        # Try to find by custom domain (strip port if present)
        clean_host = host.split(':')[0]
        # Skip root domains
        root_domains = ["localhost", "127.0.0.1", "significia.com", "www.significia.com", "app.significia.com"]
        if clean_host not in root_domains:
            tenant = db.query(Tenant).filter(Tenant.custom_domain == clean_host).first()
        
    # If tenant is found but inactive, block access
    if tenant and not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")
        
    return tenant


# ════════════════════════════════════════════════════════════════════
#  BRIDGE ARCHITECTURE — New Dependencies
# ════════════════════════════════════════════════════════════════════

def get_current_tenant(
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Depends(api_key_header),
    x_tenant_slug: str | None = __import__('fastapi').Header(None, alias="X-Tenant-Slug"),
    host: str | None = __import__('fastapi').Header(None),
) -> "Tenant":
    """
    Resolve the current tenant from JWT claims, API key, slug, or domain.
    This replaces the connector_id pattern — we no longer need a connector_id
    because the tenant's Bridge URL tells us where to send queries.
    """
    tenant = None

    # Method 1: From API key
    if x_api_key:
        hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
        api_key_obj = db.query(ApiKey).filter(ApiKey.hashed_key == hashed, ApiKey.is_active == True).first()
        if api_key_obj:
            tenant = db.query(Tenant).filter(Tenant.id == api_key_obj.tenant_id).first()

    # Method 2: From JWT token (user's tenant_id claim)
    if not tenant and token:
        try:
            payload = decode_token(token)
            token_tenant_id = payload.get("tenant_id")
            if token_tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == token_tenant_id).first()
        except Exception:
            pass

    # Method 3: From tenant slug header
    if not tenant and x_tenant_slug:
        tenant = db.query(Tenant).filter(Tenant.subdomain == x_tenant_slug).first()

    # Method 4: From Host header (Subdomain or Custom Domain)
    if not tenant and host:
        clean_host = host.split(':')[0]
        # Skip root domains
        root_domains = ["localhost", "127.0.0.1", "significia.com", "www.significia.com", "app.significia.com"]
        
        if clean_host in root_domains:
            if clean_host in ["app.significia.com"]:
                 # Explicitly resolve master tenant for admin domains
                 tenant = db.query(Tenant).filter(Tenant.subdomain == "master").first()
        else:
            # Check if it's a subdomain of localhost or significia.com
            for root in ["localhost", "significia.com"]:
                if clean_host.endswith(f".{root}"):
                    slug = clean_host.split(f".{root}")[0]
                    tenant = db.query(Tenant).filter(Tenant.subdomain == slug).first()
                    break
            
            # If not a subdomain, it must be a custom domain
            if not tenant:
                tenant = db.query(Tenant).filter(Tenant.custom_domain == clean_host).first()

    if not tenant:
        raise HTTPException(status_code=401, detail="Could not determine tenant context. Please provide X-Tenant-Slug or use a valid subdomain.")

    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    if tenant.plan_expiry_date and make_aware_ist(tenant.plan_expiry_date) < get_now_ist():
        raise HTTPException(status_code=403, detail="Your subscription plan has expired. Please renew to continue.")

    return tenant


def get_bridge_client(
    tenant: "Tenant" = Depends(get_current_tenant),
) -> BridgeClient:
    """
    Return a configured BridgeClient for the current tenant.
    This replaces get_remote_session — instead of a direct DB session,
    you get an HTTP client pointing at the tenant's Bridge.
    """
    return BridgeClient(tenant)




def get_current_client(
    token: str = Depends(oauth2_scheme),
    tenant: Tenant = Depends(get_tenant_by_slug),
    bridge: BridgeClient = Depends(get_bridge_client)
) -> dict:
    """
    Returns the current client profile from the Silo via the BridgeClient.
    Note: Now returns a dict (or we can wrap it in a Pydantic model)
    since the Master no longer has a local ClientProfile SQLAlchemy model
    that's in sync with the Silo's direct connection.
    """
    try:
        payload = decode_token(token)
        client_id: str = payload.get("sub")
        token_tenant_id: str = payload.get("tenant_id")
        
        if client_id is None or token_tenant_id != str(tenant.id):
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except ValueError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    # Since we are using Bridge Architecture, we should fetch from BridgeClient
    client_data = bridge.get(f"/master/clients/{client_id}")
    if not client_data:
        raise HTTPException(status_code=404, detail="Client not found")
        
    return client_data
