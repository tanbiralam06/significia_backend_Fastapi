"""
Bridge Management Service
─────────────────────────
Handles Bridge lifecycle: provisioning tenants, registering Bridges,
processing heartbeats, and checking Bridge health.
"""

import secrets
import uuid
from datetime import datetime, timezone as py_timezone
from typing import Optional
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.timezone import get_now_ist, to_ist

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

        now_utc = datetime.now(py_timezone.utc)
        tenant.bridge_url = bridge_url
        tenant.bridge_api_secret = api_secret
        tenant.bridge_status = "REGISTERED"
        tenant.bridge_registered_at = now_utc
        tenant.bridge_last_heartbeat = now_utc

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
        version: Optional[str] = None,
    ) -> dict:
        """Process heartbeat from the Bridge, update counts, and check billing compliance."""
        if not tenant.is_active:
            raise HTTPException(403, "Account deactivated. Please contact support.")
            
        logger = logging.getLogger("backend.bridge_service")
        
        try:
            # 1. Use client count reported by the Bridge (Source of Truth)
            # This represents the total "Internal User Seats" (Owner, Staff, Partners)
            internal_seat_count = client_count

            # 2. Update Heartbeat & Status
            now_utc = datetime.now(py_timezone.utc)
            tenant.bridge_status = "ACTIVE"
            tenant.bridge_last_heartbeat = now_utc

            # Mirror the administrative seat count for billing
            tenant.current_client_count = internal_seat_count

            # Log usage for billing audit trail
            usage = TokenUsage(
                tenant_id=tenant.id,
                metric="internal_user_seats",
                value=internal_seat_count
            )
            db.add(usage)
            db.commit()

            # Prepare IST timestamp for response/logging
            now_ist = to_ist(now_utc).strftime("%Y-%m-%d %H:%M:%S IST")
            logger.info(f"💓 Heartbeat acknowledged for {tenant.name} at {now_ist} (Seats: {client_count}, Version: {version})")

            from app.core.config import settings
            
            # Version negotiation logic
            update_available = False
            if version and settings.LATEST_BRIDGE_VERSION:
                update_available = (version != settings.LATEST_BRIDGE_VERSION)

            return {
                "acknowledged": True,
                "current_seat_usage": internal_seat_count,
                "max_client_permit": tenant.max_client_permit,
                "server_time_ist": now_ist,
                "latest_version": settings.LATEST_BRIDGE_VERSION,
                "update_available": update_available
            }
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Heartbeat processing error for tenant {tenant.id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Heartbeat failed: {str(e)}")

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
            "subdomain": tenant.subdomain,
            "bridge_url": tenant.bridge_url,
            "bridge_status": tenant.bridge_status,
            "bridge_registration_token": tenant.bridge_registration_token,
            "bridge_registered_at": tenant.bridge_registered_at,
            "bridge_last_heartbeat": tenant.bridge_last_heartbeat,
            "billing_plan": tenant.billing_plan,
            "is_active": tenant.is_active,
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
                "subdomain": t.subdomain,
                "bridge_url": t.bridge_url,
                "bridge_status": t.bridge_status,
                "bridge_registration_token": t.bridge_registration_token,
                "bridge_last_heartbeat": t.bridge_last_heartbeat,
                "max_client_permit": t.max_client_permit,
                "current_client_count": t.current_client_count,
                "billing_plan": t.billing_plan,
                "custom_domain": t.custom_domain,
                "is_active": t.is_active,
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

    # ── Update Tenant Info (Self-Service) ──────────────────────────
    @staticmethod
    def update_tenant_info(db: Session, tenant_id: uuid.UUID, custom_domain: str = None) -> dict:
        """Allow a tenant owner to update their own organization settings (e.g. custom domain)."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant record not found")

        if tenant.subdomain == "master":
            raise HTTPException(status_code=403, detail="Master organization cannot be modified via this path.")

        if custom_domain:
            # Check for uniqueness if changing domain
            custom_domain = custom_domain.lower().strip()
            if custom_domain != tenant.custom_domain:
                existing = db.query(Tenant).filter(Tenant.custom_domain == custom_domain).first()
                if existing:
                    raise HTTPException(status_code=400, detail="This custom domain is already registered to another tenant.")
            tenant.custom_domain = custom_domain
        
        db.commit()
        db.refresh(tenant)
        return {
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "subdomain": tenant.subdomain,
            "custom_domain": tenant.custom_domain,
            "bridge_status": tenant.bridge_status,
            "message": "Organization profile updated successfully"
        }

    # ── Super Admin: Toggle Tenant Active Status ────────────────────
    @staticmethod
    def toggle_tenant_status(db: Session, tenant_id: uuid.UUID, is_active: bool) -> dict:
        """Super Admin only — quickly enable or disable a tenant's access (soft kill switch)."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        
        tenant.is_active = is_active
        db.commit()
        
        status_text = "activated" if is_active else "deactivated"
        return {
            "tenant_id": str(tenant.id),
            "is_active": tenant.is_active,
            "message": f"Tenant {tenant.name} has been {status_text}."
        }

    # ── Super Admin: Update Tenant Details ──────────────────────────
    @staticmethod
    def update_tenant_admin(db: Session, tenant_id: uuid.UUID, data: dict) -> dict:
        """Super Admin only — update core tenant settings."""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        
        # Update allowed fields
        if "name" in data: tenant.name = data["name"]
        if "subdomain" in data: 
            subdomain = data["subdomain"].lower().strip()
            # Check for uniqueness if changing subdomain
            if subdomain != tenant.subdomain:
                existing = db.query(Tenant).filter(Tenant.subdomain == subdomain).first()
                if existing: raise HTTPException(400, "Subdomain already taken")
                tenant.subdomain = subdomain
        
        if "custom_domain" in data:
            custom_domain = data["custom_domain"].lower().strip() if data["custom_domain"] else None
            # Check for uniqueness if changing domain
            if custom_domain != tenant.custom_domain and custom_domain is not None:
                existing = db.query(Tenant).filter(Tenant.custom_domain == custom_domain).first()
                if existing: raise HTTPException(400, "Custom domain already in use")
            tenant.custom_domain = custom_domain
            
        if "max_client_permit" in data: tenant.max_client_permit = data["max_client_permit"]
        if "billing_plan" in data: tenant.billing_plan = data["billing_plan"]
        
        db.commit()
        db.refresh(tenant)
        
        return {
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "subdomain": tenant.subdomain,
            "custom_domain": tenant.custom_domain,
            "max_client_permit": tenant.max_client_permit,
            "billing_plan": tenant.billing_plan,
            "message": "Tenant details updated successfully."
        }
