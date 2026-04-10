"""
Email Service — Multi-Tenant Email Management for IA Masters
──────────────────────────────────────────────────────────────
Handles SMTP configuration, template rendering, and email dispatch.
All sensitive credentials are encrypted at rest using the system's Fernet keys.
"""
import uuid
import json
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from jinja2 import Template, Environment, BaseLoader, exceptions as jinja_exceptions

from app.models.email_settings import EmailSettings, EmailTemplate, EmailLog
from app.utils.encryption import encrypt_string, decrypt_string
from app.core.timezone import get_now_ist

logger = logging.getLogger("significia.email")


# ── Default Template HTML ────────────────────────────────────────────

DEFAULT_REPORT_TEMPLATE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f4f6f9; }
    .container { max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .header { background: linear-gradient(135deg, #1a365d 0%, #2d5d9f 100%); padding: 30px; color: white; text-align: center; }
    .header h1 { margin: 0; font-size: 22px; font-weight: 600; }
    .header p { margin: 5px 0 0; opacity: 0.85; font-size: 13px; }
    .body { padding: 30px; color: #333; line-height: 1.7; }
    .body p { margin: 0 0 15px; }
    .highlight { background: #f0f7ff; border-left: 4px solid #2d5d9f; padding: 12px 16px; margin: 20px 0; border-radius: 0 4px 4px 0; font-size: 14px; }
    .footer { padding: 20px 30px; background: #f9fafb; border-top: 1px solid #e5e7eb; font-size: 11px; color: #888; text-align: center; }
    .footer strong { color: #555; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{{ ia_name }}</h1>
      <p>{{ entity_name }}</p>
    </div>
    <div class="body">
      <p>Dear {{ client_name }},</p>
      <p>Please find attached your <strong>{{ report_type }}</strong> report, prepared by our team for your review.</p>
      <div class="highlight">
        Report Date: {{ date }}<br>
        SEBI Registration: {{ registration_number }}
      </div>
      <p>If you have any questions regarding this report, please do not hesitate to reach out to us.</p>
      <p>Warm regards,<br><strong>{{ ia_name }}</strong></p>
    </div>
    <div class="footer">
      <p><strong>{{ entity_name }}</strong> | SEBI Reg. No: {{ registration_number }}</p>
      <p>This is a confidential communication intended solely for the addressee.</p>
    </div>
  </div>
</body>
</html>
"""

DEFAULT_REPORT_SUBJECT = "{{ report_type }} Report — {{ client_name }} | {{ ia_name }}"


# ── Available Placeholders ───────────────────────────────────────────

AVAILABLE_PLACEHOLDERS = [
    {"key": "client_name", "label": "Client Name", "description": "Full name of the client"},
    {"key": "client_email", "label": "Client Email", "description": "Email of the client"},
    {"key": "report_type", "label": "Report Type", "description": "Type of report (e.g., Financial Analysis)"},
    {"key": "ia_name", "label": "IA Name", "description": "Name of the Investment Adviser"},
    {"key": "entity_name", "label": "Entity Name", "description": "Company/Entity name"},
    {"key": "registration_number", "label": "Registration Number", "description": "SEBI Registration Number"},
    {"key": "date", "label": "Date", "description": "Current date"},
]


class EmailService:
    """Service layer for email operations within a tenant's silo."""

    # ── SMTP Settings CRUD ─────────────────────────────────────────

    @staticmethod
    def get_settings(db: Session) -> Optional[dict]:
        """Get the current SMTP settings (singleton per tenant silo)."""
        settings = db.query(EmailSettings).first()
        if not settings:
            return None
        return {
            "id": str(settings.id),
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_username": settings.smtp_username,
            "use_tls": settings.use_tls,
            "use_ssl": settings.use_ssl,
            "from_email": settings.from_email,
            "from_name": settings.from_name,
            "is_verified": settings.is_verified,
            "last_verified_at": str(settings.last_verified_at) if settings.last_verified_at else None,
            "created_at": str(settings.created_at),
            "updated_at": str(settings.updated_at),
        }

    @staticmethod
    def save_settings(db: Session, data: dict) -> dict:
        """Create or update SMTP settings. Encrypts password before storing."""
        existing = db.query(EmailSettings).first()

        encrypted_password = encrypt_string(data["smtp_password"])

        if existing:
            existing.smtp_host = data["smtp_host"]
            existing.smtp_port = data["smtp_port"]
            existing.smtp_username = data["smtp_username"]
            existing.smtp_password_encrypted = encrypted_password
            existing.use_tls = data.get("use_tls", True)
            existing.use_ssl = data.get("use_ssl", False)
            existing.from_email = data["from_email"]
            existing.from_name = data["from_name"]
            existing.is_verified = False  # Reset verification on update
            db.commit()
            db.refresh(existing)
            result = existing
        else:
            new_settings = EmailSettings(
                smtp_host=data["smtp_host"],
                smtp_port=data["smtp_port"],
                smtp_username=data["smtp_username"],
                smtp_password_encrypted=encrypted_password,
                use_tls=data.get("use_tls", True),
                use_ssl=data.get("use_ssl", False),
                from_email=data["from_email"],
                from_name=data["from_name"],
            )
            db.add(new_settings)
            db.commit()
            db.refresh(new_settings)
            result = new_settings

        return {
            "id": str(result.id),
            "smtp_host": result.smtp_host,
            "smtp_port": result.smtp_port,
            "smtp_username": result.smtp_username,
            "use_tls": result.use_tls,
            "use_ssl": result.use_ssl,
            "from_email": result.from_email,
            "from_name": result.from_name,
            "is_verified": result.is_verified,
            "message": "Email settings saved successfully",
        }

    @staticmethod
    def update_settings(db: Session, data: dict) -> dict:
        """Partially update SMTP settings. Only updates provided fields."""
        existing = db.query(EmailSettings).first()
        if not existing:
            raise ValueError("No email settings found. Please create settings first.")

        if data.get("smtp_host") is not None:
            existing.smtp_host = data["smtp_host"]
        if data.get("smtp_port") is not None:
            existing.smtp_port = data["smtp_port"]
        if data.get("smtp_username") is not None:
            existing.smtp_username = data["smtp_username"]
        if data.get("smtp_password") and data["smtp_password"].strip():
            existing.smtp_password_encrypted = encrypt_string(data["smtp_password"])
        if data.get("use_tls") is not None:
            existing.use_tls = data["use_tls"]
        if data.get("use_ssl") is not None:
            existing.use_ssl = data["use_ssl"]
        if data.get("from_email") is not None:
            existing.from_email = data["from_email"]
        if data.get("from_name") is not None:
            existing.from_name = data["from_name"]

        existing.is_verified = False  # Reset verification on any change
        db.commit()
        db.refresh(existing)

        return {
            "id": str(existing.id),
            "smtp_host": existing.smtp_host,
            "smtp_port": existing.smtp_port,
            "smtp_username": existing.smtp_username,
            "use_tls": existing.use_tls,
            "use_ssl": existing.use_ssl,
            "from_email": existing.from_email,
            "from_name": existing.from_name,
            "is_verified": existing.is_verified,
            "message": "Email settings updated successfully",
        }

    # ── SMTP Test ──────────────────────────────────────────────────

    @staticmethod
    def test_smtp(db: Session, recipient_email: str) -> dict:
        """
        Send a test email to verify SMTP configuration.
        Returns success/failure with diagnostic info.
        """
        settings = db.query(EmailSettings).first()
        if not settings:
            return {"success": False, "message": "No SMTP settings configured.", "error": "SETTINGS_NOT_FOUND"}

        password = decrypt_string(settings.smtp_password_encrypted)

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.from_name} <{settings.from_email}>"
            msg["To"] = recipient_email
            msg["Subject"] = "✅ Significia Email Test — Configuration Verified"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background: #f4f6f9;">
              <div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h2 style="color: #1a365d; margin-top: 0;">🎉 Email Configuration Verified!</h2>
                <p style="color: #555;">Your SMTP settings are working correctly.</p>
                <div style="background: #f0f7ff; padding: 12px; border-radius: 4px; margin: 15px 0;">
                  <strong>SMTP Host:</strong> {settings.smtp_host}<br>
                  <strong>Port:</strong> {settings.smtp_port}<br>
                  <strong>From:</strong> {settings.from_name} &lt;{settings.from_email}&gt;
                </div>
                <p style="color: #888; font-size: 12px;">This is a test email from Significia Bridge.</p>
              </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            if settings.use_ssl:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
                if settings.use_tls:
                    server.starttls()

            server.login(settings.smtp_username, password)
            server.sendmail(settings.from_email, recipient_email, msg.as_string())
            server.quit()

            # Mark as verified
            settings.is_verified = True
            settings.last_verified_at = get_now_ist()
            db.commit()

            logger.info(f"✅ SMTP test successful: {settings.smtp_host}:{settings.smtp_port} → {recipient_email}")
            return {"success": True, "message": f"Test email sent successfully to {recipient_email}"}

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Auth Failed: {e}")
            return {"success": False, "message": "Authentication failed. Check username/password.", "error": str(e)}
        except smtplib.SMTPConnectError as e:
            logger.error(f"❌ SMTP Connect Failed: {e}")
            return {"success": False, "message": "Could not connect to SMTP server. Check host/port.", "error": str(e)}
        except Exception as e:
            logger.error(f"❌ SMTP Test Failed: {e}")
            return {"success": False, "message": f"Email test failed: {str(e)}", "error": str(e)}

    # ── Template CRUD ──────────────────────────────────────────────

    @staticmethod
    def list_templates(db: Session) -> List[dict]:
        """List all templates for the current tenant."""
        templates = db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()
        return [
            {
                "id": str(t.id),
                "template_name": t.template_name,
                "template_type": t.template_type,
                "subject": t.subject,
                "body_html": t.body_html,
                "is_default": t.is_default,
                "is_active": t.is_active,
                "created_at": str(t.created_at),
                "updated_at": str(t.updated_at),
            }
            for t in templates
        ]

    @staticmethod
    def create_template(db: Session, data: dict) -> dict:
        """Create a new email template."""
        # If setting as default, unset other defaults of same type
        if data.get("is_default"):
            db.query(EmailTemplate).filter(
                EmailTemplate.template_type == data["template_type"],
                EmailTemplate.is_default == True
            ).update({"is_default": False})

        template = EmailTemplate(
            template_name=data["template_name"],
            template_type=data.get("template_type", "REPORT_DELIVERY"),
            subject=data["subject"],
            body_html=data["body_html"],
            is_default=data.get("is_default", False),
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        return {
            "id": str(template.id),
            "template_name": template.template_name,
            "template_type": template.template_type,
            "subject": template.subject,
            "body_html": template.body_html,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "message": "Template created successfully",
        }

    @staticmethod
    def update_template(db: Session, template_id: uuid.UUID, data: dict) -> dict:
        """Update an existing template."""
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not template:
            raise ValueError("Template not found")

        if data.get("template_name") is not None:
            template.template_name = data["template_name"]
        if data.get("template_type") is not None:
            template.template_type = data["template_type"]
        if data.get("subject") is not None:
            template.subject = data["subject"]
        if data.get("body_html") is not None:
            template.body_html = data["body_html"]
        if data.get("is_active") is not None:
            template.is_active = data["is_active"]
        if data.get("is_default") is not None:
            if data["is_default"]:
                # Unset other defaults of same type
                db.query(EmailTemplate).filter(
                    EmailTemplate.template_type == template.template_type,
                    EmailTemplate.id != template_id,
                    EmailTemplate.is_default == True
                ).update({"is_default": False})
            template.is_default = data["is_default"]

        db.commit()
        db.refresh(template)

        return {
            "id": str(template.id),
            "template_name": template.template_name,
            "template_type": template.template_type,
            "subject": template.subject,
            "body_html": template.body_html,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "message": "Template updated successfully",
        }

    @staticmethod
    def delete_template(db: Session, template_id: uuid.UUID) -> dict:
        """Delete a template."""
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not template:
            raise ValueError("Template not found")
        db.delete(template)
        db.commit()
        return {"message": "Template deleted successfully"}

    @staticmethod
    def get_default_template(db: Session, template_type: str = "REPORT_DELIVERY") -> Optional[dict]:
        """Get the default template for a given type."""
        template = db.query(EmailTemplate).filter(
            EmailTemplate.template_type == template_type,
            EmailTemplate.is_default == True,
            EmailTemplate.is_active == True
        ).first()
        if not template:
            return None
        return {
            "id": str(template.id),
            "template_name": template.template_name,
            "template_type": template.template_type,
            "subject": template.subject,
            "body_html": template.body_html,
        }

    # ── Email Sending ──────────────────────────────────────────────

    @staticmethod
    def render_template(template_str: str, variables: dict) -> str:
        """Render a Jinja2 template string with provided variables."""
        try:
            env = Environment(loader=BaseLoader(), autoescape=True)
            tmpl = env.from_string(template_str)
            return tmpl.render(**variables)
        except jinja_exceptions.TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise ValueError(f"Template syntax error: {e}")

    @staticmethod
    def send_email(
        db: Session,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        template_id: Optional[uuid.UUID] = None,
        context_type: Optional[str] = None,
        context_id: Optional[str] = None,
        recipient_name: Optional[str] = None,
    ) -> dict:
        """
        Send an email using the tenant's SMTP settings.
        
        Args:
            attachments: List of (filename, file_bytes, content_type) tuples
        
        Returns:
            dict with status and log_id
        """
        settings = db.query(EmailSettings).first()
        if not settings:
            raise ValueError("Email settings not configured. Please configure SMTP settings first.")

        # Create log entry
        log = EmailLog(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            template_id=template_id,
            attachments_info=json.dumps([a[0] for a in attachments]) if attachments else None,
            status="PENDING",
            context_type=context_type,
            context_id=context_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        password = decrypt_string(settings.smtp_password_encrypted)

        try:
            msg = MIMEMultipart("mixed")
            msg["From"] = f"{settings.from_name} <{settings.from_email}>"
            msg["To"] = recipient_email
            msg["Subject"] = subject

            # Attach HTML body
            msg.attach(MIMEText(body_html, "html"))

            # Attach files
            if attachments:
                for filename, file_bytes, content_type in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file_bytes)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filename}")
                    msg.attach(part)

            # Connect and send
            if settings.use_ssl:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
                if settings.use_tls:
                    server.starttls()

            server.login(settings.smtp_username, password)
            server.sendmail(settings.from_email, recipient_email, msg.as_string())
            server.quit()

            # Update log
            log.status = "SENT"
            log.sent_at = get_now_ist()
            db.commit()

            logger.info(f"📧 Email sent to {recipient_email}: {subject}")
            return {
                "success": True,
                "log_id": str(log.id),
                "message": f"Email sent successfully to {recipient_email}",
            }

        except Exception as e:
            log.status = "FAILED"
            log.error_details = str(e)
            log.retry_count += 1
            db.commit()

            logger.error(f"❌ Email send failed to {recipient_email}: {e}")
            return {
                "success": False,
                "log_id": str(log.id),
                "message": f"Failed to send email: {str(e)}",
                "error": str(e),
            }

    # ── Delivery Logs ──────────────────────────────────────────────

    @staticmethod
    def get_logs(db: Session, skip: int = 0, limit: int = 50) -> dict:
        """Fetch email delivery logs with pagination."""
        total = db.query(EmailLog).count()
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).offset(skip).limit(limit).all()
        return {
            "total": total,
            "items": [
                {
                    "id": str(l.id),
                    "recipient_email": l.recipient_email,
                    "recipient_name": l.recipient_name,
                    "subject": l.subject,
                    "status": l.status,
                    "error_details": l.error_details,
                    "retry_count": l.retry_count,
                    "context_type": l.context_type,
                    "context_id": l.context_id,
                    "attachments_info": l.attachments_info,
                    "sent_at": str(l.sent_at) if l.sent_at else None,
                    "created_at": str(l.created_at),
                }
                for l in logs
            ],
        }

    # ── Helper: Get Placeholders ───────────────────────────────────

    @staticmethod
    def get_available_placeholders() -> list:
        """Return the list of available template placeholders."""
        return AVAILABLE_PLACEHOLDERS

    @staticmethod
    def get_default_report_template() -> dict:
        """Return the built-in default report delivery template."""
        return {
            "subject": DEFAULT_REPORT_SUBJECT,
            "body_html": DEFAULT_REPORT_TEMPLATE_HTML,
        }
