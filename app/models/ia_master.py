import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import SiloBase, Base
from app.core.timezone import get_now_ist

class IAMaster(Base):
    __tablename__ = "ia_master"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_of_ia: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Date] = mapped_column(Date, nullable=False)
    nature_of_entity: Mapped[str] = mapped_column(String(50), nullable=False)
    name_of_entity: Mapped[Optional[str]] = mapped_column(String(255))
    ia_registration_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    date_of_registration: Mapped[Date] = mapped_column(Date)
    date_of_registration_expiry: Mapped[Date] = mapped_column(Date)
    registered_address: Mapped[str] = mapped_column(Text)
    registered_contact_number: Mapped[str] = mapped_column(String(20))
    office_contact_number: Mapped[Optional[str]] = mapped_column(String(20))
    registered_email_id: Mapped[str] = mapped_column(String(255))
    cin_number: Mapped[Optional[str]] = mapped_column(String(100))
    bank_account_number: Mapped[str] = mapped_column(String(50))
    bank_name: Mapped[str] = mapped_column(String(255))
    bank_branch: Mapped[str] = mapped_column(String(255))
    ifsc_code: Mapped[str] = mapped_column(String(20))
    
    # ── Multi-Tenant Link ───────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    # ── Renewal Details ─────────────────────────────────────────────
    is_renewal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    renewal_certificate_no: Mapped[Optional[str]] = mapped_column(String(100))
    renewal_expiry_date: Mapped[Optional[Date]] = mapped_column(Date)
    
    # ── Relationship Manager (RM) ───────────────────────────────────
    # FK to users table (Super Admin's staff)
    relationship_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Document paths
    ia_certificate_path: Mapped[Optional[str]] = mapped_column(String(512))
    ia_signature_path: Mapped[Optional[str]] = mapped_column(String(512))
    ia_logo_path: Mapped[Optional[str]] = mapped_column(String(512))
    
    max_client_permit: Mapped[int] = mapped_column(default=10, server_default="10")
    current_client_count: Mapped[int] = mapped_column(default=0, server_default="0")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)

    # Relationships
    employees: Mapped[List["EmployeeDetails"]] = relationship(
        "EmployeeDetails", back_populates="ia_master", cascade="all, delete-orphan"
    )
    contact_persons: Mapped[List["ContactPerson"]] = relationship(
        "ContactPerson", back_populates="ia_master", cascade="all, delete-orphan"
    )

class EmployeeDetails(Base):
    __tablename__ = "employee_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ia_master_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ia_master.id", ondelete="CASCADE"), nullable=False)
    name_of_employee: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Date] = mapped_column(Date, nullable=False)
    designation: Mapped[str] = mapped_column(String(100))
    ia_registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_registration: Mapped[Optional[Date]] = mapped_column(Date)
    date_of_registration_expiry: Mapped[Optional[Date]] = mapped_column(Date)
    certificate_path: Mapped[Optional[str]] = mapped_column(String(512))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    
    # Relationships
    ia_master: Mapped["IAMaster"] = relationship("IAMaster", back_populates="employees")

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False) # UUID as string or integer ID
    changes: Mapped[Optional[str]] = mapped_column(Text)
    user_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)

    # ── SEBI-SAFE Compliance Fields ──────────────────────────────
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    field_changed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_reason_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    change_reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_version: Mapped[Optional[int]] = mapped_column(nullable=True)

class ContactPerson(Base):
    __tablename__ = "contact_persons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ia_master_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ia_master.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ia_master: Mapped["IAMaster"] = relationship("IAMaster", back_populates="contact_persons")


# ── SEBI-SAFE Compliance Models ──────────────────────────────────

class ReportHistory(Base):
    """
    Tracks every report generation event with version control.
    SEBI requirement: If a report is regenerated, maintain Version 1, Version 2… 
    with downloadable history.
    """
    __tablename__ = "report_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # risk_assessment, asset_allocation, financial_analysis
    version_number: Mapped[int] = mapped_column(default=1)
    source_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_version: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_format: Mapped[str] = mapped_column(String(10), default="pdf")
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_delivered: Mapped[bool] = mapped_column(default=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)


class IAMasterVersion(Base):
    """
    Immutable version snapshots of IA Master data.
    SEBI requirement: Every edit must create a new version while keeping old versions intact.
    """
    __tablename__ = "iamaster_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSONB snapshot of full record state
    change_reason_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    change_reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)

