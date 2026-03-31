import uuid
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.jwt import decode_token
from app.services.bridge_client import BridgeClient

from fastapi.security.api_key import APIKeyHeader
from app.models.api_key import ApiKey
import hashlib

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
    return user

def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="The user doesn't have enough privileges"
        )
    return current_user

from fastapi import Header
from app.models.tenant import Tenant
from app.models.connector import Connector
from app.utils.encryption import decrypt_string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.client import ClientProfile

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


def get_client_db(
    tenant: Tenant | None = Depends(get_tenant_by_slug),
    db: Session = Depends(get_db)
) -> Generator[Session, None, None]:
    if not tenant:
         raise HTTPException(status_code=401, detail="Tenant context required for this operation")
         
    connector = db.query(Connector).filter(
        Connector.tenant_id == tenant.id,
        Connector.type == "postgresql",
        Connector.is_active == True
    ).first()
    
    if not connector:
        # Fallback for older code where type might be used or lowercase provider
        connector = db.query(Connector).filter(
            Connector.tenant_id == tenant.id,
            Connector.is_active == True
        ).first()

    if not connector or connector.initialization_status != "READY":
        raise HTTPException(status_code=503, detail="Tenant database not available")
        
    try:
        password = decrypt_string(connector.encrypted_password)
        db_url = f"postgresql+psycopg://{connector.username}:{password}@{connector.host}:{connector.port}/{connector.database_name}"
        engine = create_engine(db_url, connect_args={"options": "-c search_path=significia_core,public"})
        RemoteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = RemoteSessionLocal()
        try:
            yield session
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database connection failed")

def get_current_client(
    token: str = Depends(oauth2_scheme),
    tenant: Tenant = Depends(get_tenant_by_slug),
    client_db: Session = Depends(get_client_db)
) -> ClientProfile:
    try:
        payload = decode_token(token)
        client_id: str = payload.get("sub")
        token_tenant_id: str = payload.get("tenant_id")
        
        if client_id is None or token_tenant_id != str(tenant.id):
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except ValueError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    client = client_db.query(ClientProfile).filter(ClientProfile.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not client.is_active:
        raise HTTPException(status_code=403, detail="Inactive client")
        
    return client


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
            user = get_current_user(db=db, token=token)
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        except HTTPException:
            pass

    # Method 3: From tenant slug header
    if not tenant and x_tenant_slug:
        tenant = db.query(Tenant).filter(Tenant.subdomain == x_tenant_slug).first()

    # Method 4: From Host header (custom domain)
    if not tenant and host:
        clean_host = host.split(':')[0]
        root_domains = ["localhost", "127.0.0.1", "significia.com", "www.significia.com", "app.significia.com"]
        if clean_host not in root_domains:
            tenant = db.query(Tenant).filter(Tenant.custom_domain == clean_host).first()

    if not tenant:
        raise HTTPException(status_code=401, detail="Could not determine tenant context")

    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")

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

