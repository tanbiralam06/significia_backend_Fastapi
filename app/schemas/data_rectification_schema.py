from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class ProposedChange(BaseModel):
    field: str
    current: Any
    proposed: Optional[Any] = None
    reason: str

class ProposedChangeInput(BaseModel):
    field: str
    current: Any
    proposed: Optional[Any] = None
    reason: str = Field(..., min_length=1)

class JustificationDetails(BaseModel):
    q1: str = Field(..., description="What is incorrect in current data?")
    q2: str = Field(..., description="Why is change required?")
    q3: str = Field(..., description="Source of revised data")

class ImpactDeclaration(BaseModel):
    financial: bool = False
    risk: bool = False
    asset_allocation: bool = False
    portfolio: bool = False
    product_basket: bool = False
    target_portfolio: bool = False
    other: bool = False
    other_details: Optional[str] = None
    remarks: Optional[str] = None

class RectificationCreate(BaseModel):
    client_id: uuid.UUID
    module: str
    record_id: str
    current_version: int
    proposed_changes: List[ProposedChangeInput]
    justification_details: JustificationDetails
    impact_declaration: ImpactDeclaration
    purpose_of_edit: Optional[str] = None
    confirmation_mode: str
    confirmation_reference: Optional[str] = None
    is_investor_requested: bool = Field(False, description="Whether the request originated from an investor")
    initiation_reason: str = Field(..., description="Reason for initiating the rectification protocol")

class RectificationUpdate(BaseModel):
    proposed_changes: Optional[List[ProposedChangeInput]] = None
    justification_details: Optional[JustificationDetails] = None
    impact_declaration: Optional[ImpactDeclaration] = None
    purpose_of_edit: Optional[str] = None
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
    purpose_of_edit: Optional[str] = None
    confirmation_mode: str = "EMAIL"
    confirmation_reference: Optional[str] = None
    is_investor_requested: bool = False
    initiation_reason: Optional[str] = None
    document_path: Optional[str] = None
    investor_request_path: Optional[str] = None
    signed_form_path: Optional[str] = None
    status: str
    requested_by_id: Optional[uuid.UUID] = None
    requested_by_name: Optional[str] = "System/Legacy"
    requested_by_role: Optional[str] = None
    approved_by_id: Optional[uuid.UUID] = None
    approved_by_name: Optional[str] = None
    approved_by_role: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True

class PaginatedRectificationResponse(BaseModel):
    records: List[RectificationResponse]
    total: int
    page: int
    limit: int
