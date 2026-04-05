from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date as date_type, datetime
from uuid import UUID

class ContactPersonBase(BaseModel):
    name: str
    designation: Optional[str] = None
    phone_number: str
    email: EmailStr
    address: Optional[str] = None

class ContactPersonCreate(ContactPersonBase):
    pass

class ClientProvisionRequest(BaseModel):
    company_name: str = Field(..., description="The name of the new client's company (tenant)")
    email: EmailStr = Field(..., description="The email address for the root owner of this tenant")
    subdomain: Optional[str] = Field(None, description="Optional subdomain (slug) for the tenant")
    
    # New registration fields
    nature_of_entity: str = "Individual"
    registration_no: str
    registration_date: date_type
    license_expiry_date: date_type
    
    # Newly added required fields
    date_of_birth: date_type
    registered_address: str
    registered_contact_number: str
    office_contact_number: Optional[str] = None
    cin_number: Optional[str] = None
    
    # Banking details
    bank_name: str
    bank_account_number: str
    bank_branch: str
    ifsc_code: str
    
    # Renewal fields
    is_renewal: bool = False
    renewal_certificate_no: Optional[str] = None
    renewal_expiry_date: Optional[date_type] = None
    
    # RM mapping
    relationship_manager_id: Optional[UUID] = None
    
    # Contact persons
    contact_persons: List[ContactPersonCreate] = []
    
    # Billing fields
    pricing_model: str = "flat_fee"
    billing_mode: str = "yearly"
    plan_expiry_date: Optional[date_type] = None
    max_client_permit: int = 5

class ClientProvisionResponse(BaseModel):
    id: str
    email: str
    tenant_id: str
    tenant_name: str
    subdomain: Optional[str]
    bridge_registration_token: str
    message: str = "Client provisioned successfully"

# Staff Management Schemas
class StaffUserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = "System User"
    phone_number: Optional[str] = "N/A"
    designation: Optional[str] = None
    address: Optional[str] = None
    role: str = "relationship_manager"
    status: str = "active"

class StaffUserCreate(StaffUserBase):
    password: str = Field(..., min_length=8)
    ia_registration_number: Optional[str] = None
    date_of_registration: Optional[date_type] = None
    date_of_registration_expiry: Optional[date_type] = None

class StaffUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    designation: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class StaffUserOut(StaffUserBase):
    id: UUID
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Activity Log Schemas
class AdminActivityLogOut(BaseModel):
    id: UUID
    admin_id: UUID
    admin_email: str
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
