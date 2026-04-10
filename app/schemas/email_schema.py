"""
Email Schemas — Pydantic Models for Email System
──────────────────────────────────────────────────
Request/Response validation for SMTP settings, templates, and delivery logs.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ── SMTP Settings ──────────────────────────────────────────────────

class EmailSettingsCreate(BaseModel):
    smtp_host: str = Field(..., min_length=1, max_length=255, description="SMTP server hostname")
    smtp_port: int = Field(587, ge=1, le=65535, description="SMTP server port")
    smtp_username: str = Field(..., min_length=1, max_length=255)
    smtp_password: str = Field(..., min_length=1, description="Plain-text password (encrypted before storage)")
    use_tls: bool = True
    use_ssl: bool = False
    from_email: EmailStr = Field(..., description="Sender email address")
    from_name: str = Field(..., min_length=1, max_length=255, description="Sender display name")


class EmailSettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = Field(None, description="Leave empty to keep existing password")
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None


class EmailSettingsRead(BaseModel):
    id: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    use_tls: bool
    use_ssl: bool
    from_email: str
    from_name: str
    is_verified: bool
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Email Templates ────────────────────────────────────────────────

class EmailTemplateCreate(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=255)
    template_type: str = Field("REPORT_DELIVERY", description="REPORT_DELIVERY | WELCOME_CLIENT | GENERAL | CUSTOM")
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = Field(..., min_length=1, description="HTML body with Jinja2 placeholders")
    is_default: bool = False


class EmailTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    template_type: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class EmailTemplateRead(BaseModel):
    id: str
    template_name: str
    template_type: str
    subject: str
    body_html: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Email Delivery Logs ───────────────────────────────────────────

class EmailLogRead(BaseModel):
    id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    template_id: Optional[str] = None
    attachments_info: Optional[str] = None
    status: str
    error_details: Optional[str] = None
    retry_count: int
    context_type: Optional[str] = None
    context_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Send Email Request ────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    """Request to send an email to a client, optionally with report attachments."""
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    template_id: Optional[str] = Field(None, description="UUID of a saved template to use")
    subject: Optional[str] = Field(None, description="Custom subject (overrides template)")
    body_html: Optional[str] = Field(None, description="Custom body (overrides template)")
    attachment_ids: Optional[List[str]] = Field(None, description="Report IDs to attach")
    attachment_formats: Optional[List[str]] = Field(default=["pdf"], description="Formats: pdf, docx, xlsx")
    context_type: Optional[str] = None
    context_id: Optional[str] = None

    # Template variables
    template_variables: Optional[dict] = Field(default_factory=dict, description="Variables for Jinja2 rendering")


class SendTestEmailRequest(BaseModel):
    """Request to send a test email to verify SMTP settings."""
    recipient_email: EmailStr


class EmailTestResult(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None
