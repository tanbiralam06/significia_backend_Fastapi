"""
Bridge Management Service
─────────────────────────
Handles Bridge lifecycle: provisioning tenants, registering Bridges,
processing heartbeats, and checking Bridge health.
"""

import secrets
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.token_usage import TokenUsage
from app.models.billing import PLAN_LIMITS


class BridgeService:

    # ── Tenant Provisioning ─────────────────────────────────────────
    @staticmethod
    def provision_tenant(
        db: Session,
        company_name: str,
        billing_plan: str = "starter",
        subdomain: Optional[str] = None,
        custom_domain: Optional[str] = None,
        max_client_permit: Optional[int] = None,
    ) -> Tenant:
        """
        Create a new tenant and generate a Bridge registration token.
        Called by Super Admin during IA onboarding.
        """
        # Validate plan
        if billing_plan not in PLAN_LIMITS:
            raise HTTPException(400, f"Invalid billing plan: {billing_plan}")

        # Resolve max clients from plan if not explicitly set
        if max_client_permit is None:
            max_client_permit = PLAN_LIMITS[billing_plan]["max_clients"]

        # Check for duplicate subdomain/domain
        if subdomain:
            existing = db.query(Tenant).filter(Tenant.subdomain == subdomain).first()
            if existing:
                raise HTTPException(400, f"Subdomain '{subdomain}' is already taken")

        if custom_domain:
            existing = db.query(Tenant).filter(Tenant.custom_domain == custom_domain).first()
            if existing:
                raise HTTPException(400, f"Custom domain '{custom_domain}' is already in use")

        # Generate a one-time registration token for the Bridge
        registration_token = Tenant.generate_bridge_token()

        tenant = Tenant(
            name=company_name,
            subdomain=subdomain,
            custom_domain=custom_domain,
            billing_plan=billing_plan,
            max_client_permit=max_client_permit,
            bridge_registration_token=registration_token,
            bridge_status="PENDING",
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        return tenant

    # ── Bridge Registration ─────────────────────────────────────────
    @staticmethod
    def register_bridge(
        db: Session,
        registration_token: str,
        bridge_url: str,
    ) -> dict:
        """
        Called by the Bridge software when it first comes online.
        The Bridge provides its registration token and public URL.
        Significia verifies the token and issues a shared API secret.
        """
        # Find the tenant by registration token
        tenant = db.query(Tenant).filter(
            Tenant.bridge_registration_token == registration_token,
            Tenant.bridge_status.in_(["PENDING", "OFFLINE"]),
        ).first()

        if not tenant:
            raise HTTPException(401, "Invalid or expired registration token")

        # Generate a shared secret for ongoing communication
        api_secret = secrets.token_urlsafe(48)

        # Update tenant with Bridge details
        tenant.bridge_url = bridge_url
        tenant.bridge_api_secret = api_secret
        tenant.bridge_status = "REGISTERED"
        tenant.bridge_registered_at = datetime.utcnow()
        tenant.bridge_last_heartbeat = datetime.utcnow()

        # Invalidate the registration token (one-time use)
        tenant.bridge_registration_token = None

        db.commit()
        db.refresh(tenant)

        return {
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "api_secret": api_secret,
        }

    # ── Bridge Heartbeat ────────────────────────────────────────────
    @staticmethod
    def process_heartbeat(
        db: Session,
        tenant: Tenant,
        client_count: int,
    ) -> dict:
        """
        Process a periodic heartbeat from the Bridge.
        Updates the tenant's status, last heartbeat time, and client count.
        """
        # Update heartbeat timestamp
        tenant.bridge_status = "ACTIVE"
        tenant.bridge_last_heartbeat = datetime.utcnow()

        # Mirror the client count for billing
        tenant.current_client_count = client_count

        # Log usage for billing audit trail
        usage = TokenUsage(
            tenant_id=tenant.id,
            metric="client_count",
            value=client_count,
        )
        db.add(usage)
        db.commit()

        return {
            "acknowledged": True,
            "max_client_permit": tenant.max_client_permit,
        }

    # ── Bridge Token Regeneration ───────────────────────────────────
    @staticmethod
    def regenerate_bridge_token(db: Session, tenant_id: uuid.UUID) -> dict:
        """
        Super Admin regenerates a Bridge registration token.
        Used when the IA loses their token or needs to re-register their Bridge.
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        new_token = Tenant.generate_bridge_token()
        tenant.bridge_registration_token = new_token
        tenant.bridge_status = "PENDING"
        tenant.bridge_url = None
        tenant.bridge_api_secret = None

        db.commit()

        return {
            "tenant_id": str(tenant.id),
            "new_token": new_token,
        }

    # ── Bridge Status ───────────────────────────────────────────────
    @staticmethod
    def get_bridge_status(db: Session, tenant_id: uuid.UUID) -> dict:
        """Get the Bridge status for a specific tenant."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        return {
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "bridge_url": tenant.bridge_url,
            "bridge_status": tenant.bridge_status,
            "bridge_registered_at": tenant.bridge_registered_at,
            "bridge_last_heartbeat": tenant.bridge_last_heartbeat,
            "max_client_permit": tenant.max_client_permit,
            "current_client_count": tenant.current_client_count,
            "billing_plan": tenant.billing_plan,
        }

    # ── List All Bridges (Super Admin Dashboard) ────────────────────
    @staticmethod
    def list_all_bridges(db: Session) -> list:
        """List all tenants with their Bridge status (for Super Admin dashboard)."""
        tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()

        return [
            {
                "tenant_id": str(t.id),
                "tenant_name": t.name,
                "bridge_url": t.bridge_url,
                "bridge_status": t.bridge_status,
                "bridge_last_heartbeat": t.bridge_last_heartbeat,
                "max_client_permit": t.max_client_permit,
                "current_client_count": t.current_client_count,
                "billing_plan": t.billing_plan,
                "custom_domain": t.custom_domain,
                "subdomain": t.subdomain,
            }
            for t in tenants
        ]

    # ── Revoke Bridge Access ────────────────────────────────────────
    @staticmethod
    def revoke_bridge(db: Session, tenant_id: uuid.UUID) -> dict:
        """
        Immediately revoke a Bridge's access.
        Used when an IA cancels their subscription or a security concern arises.
        """
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        tenant.bridge_status = "REVOKED"
        tenant.bridge_api_secret = None  # Kill the shared secret

        db.commit()

        return {
            "tenant_id": str(tenant.id),
            "message": "Bridge access has been revoked. The IA must re-register to regain access.",
        }
