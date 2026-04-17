"""
Email Settings, Templates & Delivery Logs — Silo Models
─────────────────────────────────────────────────────────
Multi-tenant email infrastructure for IA Masters.
Each tenant stores their own SMTP config, templates, and delivery audit trail.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import SiloBase
from app.core.timezone import get_now_ist


class EmailSettings(SiloBase):
    """
    Tenant-specific SMTP configuration.
    One row per tenant — singleton pattern enforced at service layer.
    """
    __tablename__ = "email_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # SMTP Connection
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)

    # Sender Identity
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)


class EmailTemplate(SiloBase):
    """
    Reusable email templates with Jinja2 placeholders.
    IA Masters can create/edit templates for different communication types.
    """
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    audit_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)

    # Template Classification
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="REPORT_DELIVERY"
    )  # REPORT_DELIVERY, WELCOME_CLIENT, GENERAL, CUSTOM

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)

    # Flags
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)


class EmailLog(SiloBase):
    """
    Delivery audit trail — every outgoing email is logged.
    Essential for SEBI compliance and IA Master's own communication tracking.
    """
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Recipient
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Content snapshot
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_audit_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)

    # Attachments info (JSON string of filenames)
    attachments_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delivery Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, SENT, FAILED
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Sender (Audit)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Context (what triggered this email)
    context_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "financial_report", "risk_report"
    context_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., report ID
    trigger_type: Mapped[str] = mapped_column(String(20), default="SYSTEM", server_default="SYSTEM")

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
