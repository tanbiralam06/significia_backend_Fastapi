from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class ProposedChange(BaseModel):
    field: str
    current: Any
    proposed: Any
    reason: str

class JustificationDetails(BaseModel):
    q1: str = Field(..., description="What is incorrect in current data?")
    q2: str = Field(..., description="Why is change required?")
    q3: str = Field(..., description="Source of revised data")

class ImpactDeclaration(BaseModel):
    financial: bool
    risk: bool
    remarks: Optional[str] = None

class RectificationCreate(BaseModel):
    client_id: uuid.UUID
    module: str
    record_id: str
    current_version: int
    proposed_changes: List[ProposedChange]
    justification_details: JustificationDetails
    impact_declaration: ImpactDeclaration
    confirmation_mode: str
    confirmation_reference: Optional[str] = None
    is_investor_requested: bool = Field(False, description="Whether the request originated from an investor")
    initiation_reason: str = Field(..., description="Reason for initiating the rectification protocol")

class RectificationUpdate(BaseModel):
    proposed_changes: Optional[List[ProposedChange]] = None
    justification_details: Optional[JustificationDetails] = None
    impact_declaration: Optional[ImpactDeclaration] = None
    confirmation_mode: Optional[str] = None
    confirmation_reference: Optional[str] = None
    is_investor_requested: Optional[bool] = None
    initiation_reason: Optional[str] = None

class RectificationResponse(BaseModel):
    id: uuid.UUID
    serial_no: str
    client_id: uuid.UUID
    module: str
    record_id: str
    current_version: int = 0
    proposed_changes: List[ProposedChange] = []
    justification_details: Optional[JustificationDetails] = None
    impact_declaration: Optional[ImpactDeclaration] = None
    confirmation_mode: str = "EMAIL"
    confirmation_reference: Optional[str] = None
    is_investor_requested: bool = False
    initiation_reason: str = "Internal Update/Legacy Record"
    document_path: Optional[str] = None
    investor_request_path: Optional[str] = None
    signed_form_path: Optional[str] = None
    status: str
    requested_by_id: Optional[uuid.UUID] = None
    requested_by_name: Optional[str] = "System/Legacy"
    approved_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None




    class Config:
        from_attributes = True
