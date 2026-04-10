"""
Email Celery Tasks — Asynchronous Email Delivery
──────────────────────────────────────────────────
Background email processing with automatic retry and exponential backoff.
"""
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger("significia.email_tasks")


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_email_async",
    max_retries=3,
    default_retry_delay=30,  # 30 seconds base delay
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff: 30s → 60s → 120s
    retry_backoff_max=300,  # Cap at 5 minutes
)
def send_email_async(self, tenant_db_url: str, email_data: dict):
    """
    Background task to send an email using a tenant's SMTP settings.
    
    Args:
        tenant_db_url: Database URL for the tenant's silo
        email_data: Dict containing:
            - recipient_email: str
            - recipient_name: Optional[str]
            - subject: str
            - body_html: str
            - attachments: Optional[List of [filename, base64_bytes, content_type]]
            - template_id: Optional[str]
            - context_type: Optional[str]
            - context_id: Optional[str]
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.email_service import EmailService
    import base64

    logger.info(f"📧 [CELERY] Processing email to {email_data.get('recipient_email')}")

    try:
        engine = create_engine(tenant_db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Decode attachments from base64 if present
        attachments = None
        raw_attachments = email_data.get("attachments")
        if raw_attachments:
            attachments = []
            for att in raw_attachments:
                filename = att[0]
                file_bytes = base64.b64decode(att[1])
                content_type = att[2]
                attachments.append((filename, file_bytes, content_type))

        result = EmailService.send_email(
            db=db,
            recipient_email=email_data["recipient_email"],
            subject=email_data["subject"],
            body_html=email_data["body_html"],
            attachments=attachments,
            template_id=email_data.get("template_id"),
            context_type=email_data.get("context_type"),
            context_id=email_data.get("context_id"),
            recipient_name=email_data.get("recipient_name"),
        )

        db.close()
        engine.dispose()

        if not result.get("success"):
            raise Exception(result.get("message", "Email send failed"))

        logger.info(f"✅ [CELERY] Email sent successfully to {email_data.get('recipient_email')}")
        return result

    except Exception as e:
        logger.error(f"❌ [CELERY] Email task failed (attempt {self.request.retries + 1}): {e}")
        raise  # Celery will auto-retry due to autoretry_for
