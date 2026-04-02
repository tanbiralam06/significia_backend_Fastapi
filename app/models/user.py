import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, INET

from app.database.base import Base
from app.core.timezone import get_now_ist

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    tenant = relationship("Tenant", lazy="joined")

    @property
    def company_name(self) -> str:
        return self.tenant.name if self.tenant else ""

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Renamed from email_verified

    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(50), default="user")
    status: Mapped[str] = mapped_column(String(50), default="active")

    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False) # Renamed from two_factor_enabled
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip = mapped_column(INET, nullable=True)

    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verify_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_now_ist)
    refresh_token_version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_now_ist, onupdate=get_now_ist)
