"""
Client Authentication Routes — Bridge Architecture
───────────────────────────────────────────────────
Client login now verifies credentials through the Bridge.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    get_bridge_client, get_current_tenant,
    get_client_db, get_tenant_by_slug, get_current_client
)
from app.services.bridge_client import BridgeClient
from app.models.tenant import Tenant
from app.schemas.client_schema import ClientLoginRequest, ClientTokenResponse, ClientResponse
from app.services.client_auth_service import ClientAuthService
from app.models.client import ClientProfile

router = APIRouter()
client_auth_service = ClientAuthService()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES
# ════════════════════════════════════════════════════════════════════

@router.post("/bridge/login", response_model=dict)
async def login_bridge(
    request: ClientLoginRequest,
    tenant: Tenant = Depends(get_current_tenant),
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Client login via the Bridge.
    The Bridge checks credentials against the local database
    and returns the client profile for JWT token generation.
    """
    # Ask the Bridge to verify the client's credentials
    client_data = await bridge.post("/api/auth/verify-client", {
        "email": request.email,
    })

    # Verify password on this side (password_hash came from Bridge)
    from app.core.security import verify_password
    if not verify_password(request.password, client_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token locally
    from app.core.jwt import create_access_token, create_refresh_token
    token_data = {
        "sub": client_data["id"],
        "tenant_id": str(tenant.id),
        "role": "client",
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "client_name": client_data["client_name"],
    }


# ════════════════════════════════════════════════════════════════════
#  LEGACY ROUTES (kept during transition)
# ════════════════════════════════════════════════════════════════════

@router.post("/login", response_model=ClientTokenResponse)
def login(
    request: ClientLoginRequest, 
    tenant: Tenant = Depends(get_tenant_by_slug),
    client_db: Session = Depends(get_client_db)
):
    """
    Login endpoint specifically for clients (legacy).
    Relies on X-Tenant-Slug header via dependencies to route to correct DB.
    """
    return client_auth_service.authenticate_client(client_db, request, tenant)

@router.get("/me", response_model=ClientResponse)
def get_client_me(current_client: ClientProfile = Depends(get_current_client)):
    return current_client
