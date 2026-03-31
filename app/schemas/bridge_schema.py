"""
Bridge-related Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# ── Bridge Registration (called by the Bridge itself) ──────────────
class BridgeRegisterRequest(BaseModel):
    """Sent by the Bridge when it first comes online to register itself."""
    registration_token: str = Field(..., description="One-time token provided by Super Admin during onboarding")
    bridge_url: str = Field(..., description="The public URL where this Bridge can be reached (e.g., https://bridge.bunty.com)")


class BridgeRegisterResponse(BaseModel):
    """Returned to the Bridge after successful registration."""
    tenant_id: str
    tenant_name: str
    api_secret: str = Field(..., description="Shared secret for ongoing authenticated communication")
    message: str = "Bridge registered successfully"


# ── Bridge Heartbeat (periodic health signal from Bridge) ──────────
class BridgeHeartbeat(BaseModel):
    """Periodic heartbeat sent by Bridge to confirm it is alive."""
    tenant_id: str
    client_count: int = Field(0, description="Current number of clients in the IA's database")
    status: str = Field("healthy", description="Bridge self-reported status")


class BridgeHeartbeatResponse(BaseModel):
    """Response to a heartbeat from the Bridge."""
    acknowledged: bool = True
    max_client_permit: int = Field(..., description="Current client limit for this tenant's plan")


# ── Bridge Status (for Super Admin dashboard) ──────────────────────
class BridgeStatusResponse(BaseModel):
    """Bridge status as seen by the Super Admin."""
    tenant_id: str
    tenant_name: str
    bridge_url: Optional[str] = None
    bridge_status: str
    bridge_registered_at: Optional[datetime] = None
    bridge_last_heartbeat: Optional[datetime] = None
    max_client_permit: int
    current_client_count: int
    billing_plan: str


# ── Tenant Provisioning (updated for Bridge model) ─────────────────
class TenantProvisionRequest(BaseModel):
    """Super Admin provisions a new IA tenant."""
    company_name: str = Field(..., description="The IA firm's name")
    billing_plan: str = Field("starter", description="Pricing tier: free, starter, growth, pro, enterprise")
    subdomain: Optional[str] = Field(None, description="Subdomain for the IA (e.g., 'bunty' for bunty.significia.com)")
    custom_domain: Optional[str] = Field(None, description="Custom domain (e.g., bunty.com)")
    max_client_permit: int = Field(5, description="Maximum number of clients allowed")


class TenantProvisionResponse(BaseModel):
    """Response after provisioning a new tenant."""
    tenant_id: str
    tenant_name: str
    bridge_registration_token: str = Field(..., description="Give this token to the IA to configure their Bridge")
    instructions: str = "Provide this token to the IA. They will use it when setting up the Significia Bridge on their server."


# ── Bridge Token Regeneration ──────────────────────────────────────
class BridgeTokenRegenerateResponse(BaseModel):
    """Response when Super Admin regenerates a Bridge registration token."""
    tenant_id: str
    new_token: str
    message: str = "New Bridge registration token generated. Previous token is now invalid."
