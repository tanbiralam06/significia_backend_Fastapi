from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from uuid import UUID

# Employee Details Schemas
class EmployeeBase(BaseModel):
    name_of_employee: str
    date_of_birth: Optional[date] = None
    designation: str
    ia_registration_number: str
    date_of_registration: Optional[date] = None
    date_of_registration_expiry: Optional[date] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Age must be at least 18 years")
        return v

class EmployeeCreate(EmployeeBase):
    date_of_birth: date

class EmployeeRead(EmployeeBase):
    id: UUID
    ia_master_id: UUID
    certificate_path: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# IA Master Schemas
class IAMasterBase(BaseModel):
    name_of_ia: str
    date_of_birth: Optional[date] = None
    nature_of_entity: str
    name_of_entity: Optional[str] = None
    basl_membership_id: str
    ia_registration_number: str
    date_of_registration: Optional[date] = None
    date_of_registration_expiry: Optional[date] = None
    registered_address: str
    registered_contact_number: str
    office_contact_number: Optional[str] = None
    registered_email_id: EmailStr
    cin_number: Optional[str] = None
    bank_account_number: str
    bank_name: str
    bank_branch: str
    ifsc_code: str

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Age must be at least 18 years")
        return v

class IAMasterCreate(IAMasterBase):
    date_of_birth: date

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

class IAMasterListResponse(BaseModel):
    items: List[IAMasterRead]
    total_count: int

# Audit Trail Schemas
class AuditTrailBase(BaseModel):
    action_type: str
    table_name: str
    record_id: str
    changes: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    # ── SEBI-SAFE Compliance Fields ──
    user_id: Optional[UUID] = None
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_reason_type: Optional[str] = None
    change_reason_text: Optional[str] = None
    entity_version: Optional[int] = None

class AuditTrailCreate(AuditTrailBase):
    pass

class AuditTrailRead(AuditTrailBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Validation Response
class IANumberValidationResponse(BaseModel):
    exists: bool


# ── SEBI-SAFE Compliance Schemas ──────────────────────────────

class ReportHistoryRead(BaseModel):
    """Schema for report version tracking responses."""
    id: UUID
    client_id: Optional[UUID] = None
    report_type: str
    version_number: int
    source_record_id: Optional[UUID] = None
    source_version: Optional[int] = None
    file_path: Optional[str] = None
    file_format: str = "pdf"
    change_summary: Optional[str] = None
    is_delivered: bool = False
    delivered_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class IAMasterVersionRead(BaseModel):
    """Schema for immutable IA Master version snapshots."""
    id: UUID
    original_user_id: UUID
    version_number: int
    snapshot: dict
    change_reason_type: Optional[str] = None
    change_reason_text: Optional[str] = None
    changed_by: Optional[UUID] = None
    changed_fields: Optional[list] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChangeSummaryEntry(BaseModel):
    """A single entry in the change history summary."""
    version: int
    summary: str
    reason_type: Optional[str] = None
    reason_text: Optional[str] = None
    changed_fields: Optional[list] = None
    timestamp: datetime

class ChangeSummaryResponse(BaseModel):
    """Response for the change summary endpoint."""
    change_history: list[ChangeSummaryEntry]
    total_versions: int

