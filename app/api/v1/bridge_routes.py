"""
Bridge API Routes
─────────────────
Two groups of endpoints:

1. Super Admin routes (app.significia.com) — manage Bridges
2. Bridge-facing routes — called by the Bridge software itself
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_super_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.bridge_schema import (
    BridgeRegisterRequest,
    BridgeRegisterResponse,
    BridgeHeartbeat,
    BridgeHeartbeatResponse,
    BridgeStatusResponse,
    TenantProvisionRequest,
    TenantProvisionResponse,
    BridgeTokenRegenerateResponse,
)
from app.services.bridge_service import BridgeService

router = APIRouter()
bridge_service = BridgeService()


# ════════════════════════════════════════════════════════════════════
#  SUPER ADMIN ENDPOINTS (app.significia.com)
# ════════════════════════════════════════════════════════════════════

@router.post("/tenants/provision", response_model=TenantProvisionResponse, status_code=201)
def provision_tenant(
    request: TenantProvisionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """
    Provision a new IA tenant and generate a Bridge registration token.
    The token must be given to the IA to configure their Bridge.
    """
    tenant = bridge_service.provision_tenant(
        db=db,
        company_name=request.company_name,
        billing_plan=request.billing_plan,
        subdomain=request.subdomain,
        custom_domain=request.custom_domain,
        max_client_permit=request.max_client_permit,
    )
    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "bridge_registration_token": tenant.bridge_registration_token,
        "instructions": (
            "Give this token to the IA. They will enter it during Bridge setup. "
            "This token can only be used once."
        ),
    }


@router.get("/tenants/bridges", response_model=List[BridgeStatusResponse])
def list_all_bridges(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """List all tenants with their Bridge connection status."""
    return bridge_service.list_all_bridges(db)


@router.get("/tenants/{tenant_id}/bridge", response_model=BridgeStatusResponse)
def get_bridge_status(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """Get Bridge status for a specific tenant."""
    return bridge_service.get_bridge_status(db, tenant_id)


@router.post("/tenants/{tenant_id}/regenerate-token", response_model=BridgeTokenRegenerateResponse)
def regenerate_bridge_token(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """
    Regenerate a Bridge registration token for an IA.
    This invalidates the previous token and resets the Bridge to PENDING status.
    The IA must re-register their Bridge with the new token.
    """
    result = bridge_service.regenerate_bridge_token(db, tenant_id)
    return result


@router.post("/tenants/{tenant_id}/revoke")
def revoke_bridge(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """
    Immediately revoke a Bridge's access.
    The IA's portal will stop working until they re-register.
    """
    return bridge_service.revoke_bridge(db, tenant_id)


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-FACING ENDPOINTS (called by the Bridge software)
# ════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=BridgeRegisterResponse)
def register_bridge(
    request: BridgeRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Called by the Bridge software when it first comes online.
    The Bridge provides its one-time registration token and its public URL.
    Significia responds with a shared API secret for ongoing communication.
    
    This endpoint is PUBLIC (no auth required) because the Bridge
    doesn't have credentials yet — it's using the registration token.
    """
    result = bridge_service.register_bridge(
        db=db,
        registration_token=request.registration_token,
        bridge_url=request.bridge_url,
    )
    return result


@router.post("/heartbeat", response_model=BridgeHeartbeatResponse)
def bridge_heartbeat(
    heartbeat: BridgeHeartbeat,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Periodic heartbeat from the Bridge.
    Reports current client count and status.
    Significia uses this for billing and monitoring.
    """
    # Extract API secret from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    api_secret = authorization.replace("Bearer ", "")

    # Find tenant by the shared API secret
    tenant = db.query(Tenant).filter(
        Tenant.bridge_api_secret == api_secret,
        Tenant.id == uuid.UUID(heartbeat.tenant_id),
    ).first()

    if not tenant:
        raise HTTPException(401, "Invalid Bridge credentials")

    if tenant.bridge_status == "REVOKED":
        raise HTTPException(403, "Bridge access has been revoked")

    result = bridge_service.process_heartbeat(
        db=db,
        tenant=tenant,
        client_count=heartbeat.client_count,
    )
    return result
