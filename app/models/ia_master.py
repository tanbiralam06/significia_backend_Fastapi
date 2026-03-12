import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base

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
    
    # Document paths
    ia_certificate_path: Mapped[Optional[str]] = mapped_column(String(512))
    ia_signature_path: Mapped[Optional[str]] = mapped_column(String(512))
    ia_logo_path: Mapped[Optional[str]] = mapped_column(String(512))
    
    max_client_permit: Mapped[int] = mapped_column(default=10, server_default="10")
    current_client_count: Mapped[int] = mapped_column(default=0, server_default="0")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employees: Mapped[List["EmployeeDetails"]] = relationship(
        "EmployeeDetails", back_populates="ia_master", cascade="all, delete-orphan"
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
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ia_master: Mapped["IAMaster"] = relationship("IAMaster", back_populates="employees")

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Changed client_id to tenant_id to match our architecture if needed, 
    # but for now keeping it generic as per the original script if the original script meant 'subject'
    # Actually original script had client_id REFERENCES client_profile(id). 
    # I'll use a generic record_id and table_name.
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False) # UUID as string or integer ID
    changes: Mapped[Optional[str]] = mapped_column(Text)
    user_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
