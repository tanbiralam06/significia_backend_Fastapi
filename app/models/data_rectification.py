import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Text, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import SiloBase
from app.core.timezone import get_now_ist

class DataRectification(SiloBase):
    """
    Stores formal data rectification requests, their justifications, 
    and links to physical signed authorization evidence.
    """
    __tablename__ = "data_rectifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Serial No: E-YYYYMMDD-XXXX
    serial_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    
    # Initiation Reason
    initiation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Module: RISK, FINANCIAL, CLIENT, ASSET
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Source Record Identification
    record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_version: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    
    # Proposed Changes: [{ "field": "pan", "current": "OLD", "proposed": "NEW", "reason": "..." }]
    proposed_changes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    
    # Justification: { "q1": "...", "q2": "...", "q3": "..." }
    justification_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Impact: { "financial": true, "risk": false, "remarks": "..." }
    impact_declaration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Confirmation Mode: WRITTEN, VERBAL, NA
    confirmation_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    confirmation_reference: Mapped[Optional[str]] = mapped_column(Text)
    
    # Evidence: Path to scanned signed document
    document_path: Mapped[Optional[str]] = mapped_column(String(512))
    
    # Status: DRAFT, UPDATED
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    
    # Signatures / Approvals
    signature_method: Mapped[str] = mapped_column(String(20), default="CHECKBOX", server_default="CHECKBOX")
    
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)

    client = relationship("ClientProfile", foreign_keys=[client_id])
