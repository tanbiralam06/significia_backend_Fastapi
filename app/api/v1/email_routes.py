"""
Email Routes — Bridge Architecture
─────────────────────────────────────
API endpoints for IA Master email management:
- SMTP settings configuration
- Email template CRUD
- Test email delivery
- Delivery logs
- Send email (with optional report attachments)

All endpoints proxy through the Bridge to the tenant's silo database.
"""
import uuid
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_bridge_client, get_current_user, get_current_ia_owner
from app.services.bridge_client import BridgeClient

logger = logging.getLogger("significia.email_routes")

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  SMTP SETTINGS
# ══════════════════════════════════════════════════════════════════

@router.get("/settings")
async def get_email_settings(
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """Get current SMTP settings for this tenant."""
    try:
        result = await bridge.get("/email/settings")
        return result
    except HTTPException as e:
        if e.status_code == 404:
            return None
        raise


@router.put("/settings")
async def save_email_settings(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Create or update SMTP settings. Owner only."""
    return await bridge.put("/email/settings", payload)


@router.patch("/settings")
async def update_email_settings(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Partially update SMTP settings. Owner only."""
    return await bridge.patch("/email/settings", payload)


@router.post("/settings/test")
async def test_email_settings(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Send a test email to verify SMTP configuration."""
    return await bridge.post("/email/settings/test", payload)


# ══════════════════════════════════════════════════════════════════
#  EMAIL TEMPLATES
# ══════════════════════════════════════════════════════════════════

@router.get("/templates")
async def list_templates(
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """List all email templates."""
    return await bridge.get("/email/templates")


@router.post("/templates")
async def create_template(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Create a new email template. Owner only."""
    return await bridge.post("/email/templates", payload)


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Update an existing email template. Owner only."""
    return await bridge.put(f"/email/templates/{template_id}", payload)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_ia_owner),
):
    """Delete an email template. Owner only."""
    return await bridge.delete(f"/email/templates/{template_id}")


@router.get("/templates/default")
async def get_default_template(
    template_type: str = "REPORT_DELIVERY",
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """Get the default built-in template for a given type."""
    return await bridge.get(f"/email/templates/default", params={"template_type": template_type})


@router.get("/placeholders")
async def get_placeholders(
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """Get the list of available template placeholders."""
    return await bridge.get("/email/placeholders")


# ══════════════════════════════════════════════════════════════════
#  SEND EMAIL
# ══════════════════════════════════════════════════════════════════

@router.post("/send")
async def send_email(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """
    Send an email to a client (with optional report attachments).
    Supports both synchronous and async (Celery) delivery.
    """
    return await bridge.post("/email/send", payload)


@router.post("/send/report")
async def send_report_email(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """
    Send a report to a client via email.
    
    Expected payload:
    {
        "client_id": "uuid",
        "report_type": "financial_analysis | risk_assessment | asset_allocation",
        "report_id": "uuid",
        "formats": ["pdf", "docx"],
        "template_id": "optional-uuid",
        "custom_message": "optional override"
    }
    """
    return await bridge.post("/email/send/report", payload)


@router.post("/onboarding/send")
async def send_onboarding_email(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """
    Manually trigger the onboarding email for a client.
    This request is proxied to the tenant's Bridge.
    """
    return await bridge.post("/email/onboarding/send", payload)


# ══════════════════════════════════════════════════════════════════
#  DELIVERY LOGS
# ══════════════════════════════════════════════════════════════════

@router.get("/logs")
async def get_email_logs(
    skip: int = 0,
    limit: int = 50,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """Get email delivery logs with pagination."""
    return await bridge.get("/email/logs", params={"skip": skip, "limit": limit})
