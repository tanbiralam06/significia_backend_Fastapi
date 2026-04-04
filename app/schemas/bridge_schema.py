from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class BridgeRegisterRequest(BaseModel):
    registration_token: str
    bridge_url: str

class BridgeRegisterResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    api_secret: str

class BridgeHeartbeat(BaseModel):
    tenant_id: str
    client_count: int

class BridgeHeartbeatResponse(BaseModel):
    acknowledged: bool
    max_client_permit: int
    server_time_ist: str

class BridgeStatusResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    subdomain: Optional[str] = None
    bridge_url: Optional[str] = None
    bridge_status: str
    bridge_registration_token: Optional[str] = None
    bridge_registered_at: Optional[datetime] = None
    bridge_last_heartbeat: Optional[datetime] = None
    max_client_permit: int
    current_client_count: int
    billing_plan: str
    custom_domain: Optional[str] = None
    is_active: bool = True

class TenantProvisionRequest(BaseModel):
    company_name: str
    billing_plan: str = "starter"
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    max_client_permit: Optional[int] = None

class TenantProvisionResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    bridge_registration_token: str
    instructions: str

class BridgeTokenRegenerateResponse(BaseModel):
    tenant_id: str
    new_token: str

class TenantUpdateRequest(BaseModel):
    custom_domain: Optional[str] = None

class TenantUpdateResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    bridge_status: str
    message: str

class TenantAdminUpdateRequest(BaseModel):
    name: Optional[str] = None
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    max_client_permit: Optional[int] = None
    billing_plan: Optional[str] = None

class TenantStatusToggleRequest(BaseModel):
    is_active: bool
