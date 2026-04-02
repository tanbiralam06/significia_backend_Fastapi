"""
Client Authentication Routes — Bridge Architecture
───────────────────────────────────────────────────
Client login now verifies credentials through the Bridge.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    get_bridge_client, get_current_tenant,
    get_client_db, get_tenant_by_slug, get_current_client,
    oauth2_scheme
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
    request: Request,
    login_data: ClientLoginRequest,
    tenant: Tenant = Depends(get_current_tenant),
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Unified tenant-domain login via the Bridge.
    Tries Client logic first, then falls back to IA Staff (Master/Owner) logic.
    Verification (including password & lockout) is now handled entirely on the Bridge.
    """
    user_id = None
    role = "client"
    user_name = "User"
    client_ip = request.client.host if request.client else "0.0.0.0"

    try:
        # 1. Attempt Client Verification (Now including password & IP on Bridge)
        payload = {
            "email": login_data.email,
            "password": login_data.password,
            "ip": client_ip
        }
        client_data = await bridge.post("/auth/verify-client", payload)
        user_id = client_data["id"]
        role = "client"
        user_name = client_data["name"]
        
    except HTTPException as e:
        if e.status_code == 401:
            # 2. Fallback: Attempt IA Master / Staff Verification
            try:
                ia_data = await bridge.post("/auth/verify-ia-user", {
                    "email": login_data.email,
                    "password": login_data.password,
                    "ip": client_ip
                })
                user_id = ia_data["id"]
                user_name = ia_data["name"]
                role = ia_data["role"]
            except HTTPException as inner_e:
                if inner_e.status_code == 423:
                    raise inner_e # Pass through lockout
                # If fallback also fails, raise 401
                raise HTTPException(status_code=401, detail="Invalid email or password")
        elif e.status_code == 423:
            raise e # Pass through lockout
        else:
            raise

    # Generate JWT token locally using the resolved identity and role
    from app.core.jwt import create_access_token, create_refresh_token
    access_token = create_access_token(
        subject=str(user_id),
        tenant_id=str(tenant.id),
        role=role
    )
    refresh_token = create_refresh_token(
        subject=str(user_id),
        tenant_id=str(tenant.id)
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user_id),
            "name": user_name,
            "role": role,
            "email": login_data.email,
        },
        "subdomain": tenant.subdomain,
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

@router.get("/me")
async def get_client_me(
    token: str = Depends(oauth2_scheme),
    tenant: Tenant = Depends(get_current_tenant),
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Get the currently logged-in user profile from the Bridge.
    Works for both IA Masters (Owners) and Clients via the unified Bridge profile endpoint.
    """
    from app.core.jwt import decode_token
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Fetch the complete unified profile from the Bridge
        profile = await bridge.get(f"/auth/profile/{user_id}")
        return profile
        
    except Exception as e:
        import logging
        logging.error(f"Error fetching bridge profile: {e}")
        raise HTTPException(status_code=401, detail="Could not retrieve profile from Bridge")
