from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID

# Employee Details Schemas
class EmployeeBase(BaseModel):
    name_of_employee: str
    designation: str
    ia_registration_number: str
    date_of_registration: Optional[date] = None
    date_of_registration_expiry: Optional[date] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeRead(EmployeeBase):
    id: UUID
    ia_master_id: UUID
    certificate_path: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# IA Master Schemas
class IAMasterBase(BaseModel):
    name_of_ia: str
    nature_of_entity: str
    name_of_entity: Optional[str] = None
    ia_registration_number: str
    date_of_registration: date
    date_of_registration_expiry: date
    registered_address: str
    registered_contact_number: str
    office_contact_number: Optional[str] = None
    registered_email_id: EmailStr
    cin_number: Optional[str] = None
    bank_account_number: str
    bank_name: str
    bank_branch: str
    ifsc_code: str

class IAMasterCreate(IAMasterBase):
    pass

class IAMasterPermitUpdate(BaseModel):
    max_client_permit: int = Field(..., gt=0, description="The new maximum number of allowed clients.")

class IAMasterRead(IAMasterBase):
    id: UUID
    ia_certificate_path: Optional[str] = None
    ia_signature_path: Optional[str] = None
    ia_logo_path: Optional[str] = None
    max_client_permit: int
    current_client_count: int
    created_at: datetime
    updated_at: datetime
    employees: List[EmployeeRead] = []
    model_config = ConfigDict(from_attributes=True)

# Audit Trail Schemas
class AuditTrailBase(BaseModel):
    action_type: str
    table_name: str
    record_id: str
    changes: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None

class AuditTrailCreate(AuditTrailBase):
    pass

class AuditTrailRead(AuditTrailBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Validation Response
class IANumberValidationResponse(BaseModel):
    exists: bool
