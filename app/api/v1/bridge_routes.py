"""
Bridge API Routes
─────────────────
Two groups of endpoints:

1. Super Admin routes (app.significia.com) — manage Bridges
2. Bridge-facing routes — called by the Bridge software itself
3. Tenant self-service routes (IA Owners)
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("backend.bridge_routes")

from app.api.deps import get_db, get_current_super_admin, get_current_ia_owner
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
    TenantUpdateRequest,
    TenantUpdateResponse,
    TenantAdminUpdateRequest,
    TenantStatusToggleRequest,
)
from app.services.bridge_service import BridgeService

router = APIRouter()
bridge_service = BridgeService()


# ════════════════════════════════════════════════════════════════════
#  TENANT SELF-SERVICE (Organization Owners)
# ════════════════════════════════════════════════════════════════════

@router.patch("/tenants/me", response_model=TenantUpdateResponse)
def update_my_tenant(
    request: TenantUpdateRequest,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_ia_owner),
):
    """
    Allow an IA Owner to update their own organization settings.
    Currently supports: custom_domain.
    """
    return bridge_service.update_tenant_info(
        db=db, 
        tenant_id=current_owner.tenant_id, 
        custom_domain=request.custom_domain
    )


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


@router.patch("/tenants/{tenant_id}", response_model=TenantUpdateResponse)
def update_tenant_admin(
    tenant_id: uuid.UUID,
    request: TenantAdminUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """Super Admin only — update core tenant settings (name, limit, plan, etc.)."""
    result = bridge_service.update_tenant_admin(db, tenant_id, request.dict(exclude_unset=True))
    result["bridge_status"] = "N/A" # update_tenant_admin doesn't return bridge_status by default
    return result


@router.post("/tenants/{tenant_id}/status")
def toggle_tenant_status(
    tenant_id: uuid.UUID,
    request: TenantStatusToggleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin),
):
    """Super Admin only — activate or deactivate a tenant."""
    return bridge_service.toggle_tenant_status(db, tenant_id, request.is_active)


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
    try:
        # Extract API secret from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid authorization header")
        api_secret = authorization.replace("Bearer ", "")

        # Find tenant by the shared API secret
        tenant_uuid = uuid.UUID(heartbeat.tenant_id)
        tenant = db.query(Tenant).filter(
            Tenant.bridge_api_secret == api_secret,
            Tenant.id == tenant_uuid,
        ).first()

        if not tenant:
            logger.warning(f"❌ Heartbeat failed: Invalid credentials for tenant {heartbeat.tenant_id}")
            raise HTTPException(401, "Invalid Bridge credentials")

        if tenant.bridge_status == "REVOKED":
            logger.warning(f"❌ Heartbeat failed: Bridge revoked for {tenant.name}")
            raise HTTPException(403, "Bridge access has been revoked")

        result = bridge_service.process_heartbeat(
            db=db,
            tenant=tenant,
            client_count=heartbeat.client_count,
        )
        return result
    except ValueError as e:
        logger.error(f"❌ Heartbeat failed: Invalid UUID string: {heartbeat.tenant_id}")
        raise HTTPException(status_code=400, detail=f"Invalid tenant_id format: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Heartbeat route crash: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal route error: {str(e)}")
