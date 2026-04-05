import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Float, ForeignKey, Text, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import SiloBase
from app.core.timezone import get_now_ist

class ClientProfile(SiloBase):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Personal Information
    client_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Date] = mapped_column(Date, nullable=False)
    pan_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    marital_status: Mapped[str] = mapped_column(String(50), nullable=False)
    nationality: Mapped[str] = mapped_column(String(100), nullable=False)
    residential_status: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_residency: Mapped[str] = mapped_column(String(100), nullable=False)
    pep_status: Mapped[str] = mapped_column(String(100), nullable=False)
    father_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mother_name: Mapped[str] = mapped_column(String(255), nullable=False)
    spouse_name: Mapped[Optional[str]] = mapped_column(String(255))
    spouse_dob: Mapped[Optional[date]] = mapped_column(Date)
    aadhar_number: Mapped[Optional[str]] = mapped_column(String(12))
    passport_number: Mapped[Optional[str]] = mapped_column(String(50))

    # Financial Information
    annual_income: Mapped[float] = mapped_column(Float, nullable=False)
    net_worth: Mapped[float] = mapped_column(Float, nullable=False)
    income_source: Mapped[str] = mapped_column(String(100), nullable=False)
    fatca_compliance: Mapped[str] = mapped_column(String(100), nullable=False)
    existing_portfolio_value: Mapped[float] = mapped_column(Float, default=0.0)
    existing_portfolio_composition: Mapped[Optional[str]] = mapped_column(Text)

    # Banking Details
    bank_account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)
    demat_account_number: Mapped[Optional[str]] = mapped_column(String(100))
    trading_account_number: Mapped[Optional[str]] = mapped_column(String(100))

    # Investment Profile
    risk_profile: Mapped[str] = mapped_column(String(100), nullable=False)
    investment_experience: Mapped[str] = mapped_column(String(100), nullable=False)
    investment_objectives: Mapped[str] = mapped_column(Text, nullable=False)
    investment_horizon: Mapped[str] = mapped_column(String(100), nullable=False)
    liquidity_needs: Mapped[str] = mapped_column(String(100), nullable=False)

    # Metadata
    advisor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    advisor_registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    client_date: Mapped[Date] = mapped_column(Date, nullable=False, default=date.today)
    nominee_name: Mapped[Optional[str]] = mapped_column(String(255))
    nominee_relationship: Mapped[Optional[str]] = mapped_column(String(100))
    previous_advisor_name: Mapped[Optional[str]] = mapped_column(String(255))
    referral_source: Mapped[Optional[str]] = mapped_column(String(100))
    declaration_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    agreement_date: Mapped[Optional[Date]] = mapped_column(Date)
    client_signature_path: Mapped[Optional[str]] = mapped_column(String(512))
    advisor_signature_path: Mapped[Optional[str]] = mapped_column(String(512))

    # KYC & IPV Details
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ckyc_number: Mapped[Optional[str]] = mapped_column(String(50))
    ipv_done_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("employee_details.id", ondelete="SET NULL"), nullable=True
    )
    ipv_date: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)

    # Assignment
    assigned_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("employee_details.id", ondelete="SET NULL"), nullable=True
    )
    assigned_employee: Mapped[Optional["EmployeeDetails"]] = relationship("EmployeeDetails", foreign_keys=[assigned_employee_id])
    ipv_done_by: Mapped[Optional["EmployeeDetails"]] = relationship("EmployeeDetails", foreign_keys=[ipv_done_by_id])

    # Relationships
    documents: Mapped[list["ClientDocument"]] = relationship(
        "ClientDocument", back_populates="client", cascade="all, delete-orphan"
    )
    audit_trails: Mapped[list["ClientAuditTrail"]] = relationship(
        "ClientAuditTrail", back_populates="client", cascade="all, delete-orphan"
    )

class ClientDocument(SiloBase):
    __tablename__ = "client_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    
    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile", back_populates="documents")

class ClientAuditTrail(SiloBase):
    __tablename__ = "client_audit_trail"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    changes: Mapped[Optional[dict]] = mapped_column(JSONB)
    user_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile", back_populates="audit_trails")
