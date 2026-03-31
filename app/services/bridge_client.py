"""
Bridge Communication Client
────────────────────────────
This module handles ALL communication between the Significia Backend and IA Bridges.
Every request to an IA's data must go through this client — no direct DB connections.

The Bridge Client:
  1. Resolves the correct Bridge URL for a given tenant
  2. Authenticates requests using the shared bridge_api_secret
  3. Sends structured queries and receives structured responses
  4. Handles timeouts, retries, and error formatting
  5. Logs all communication for audit purposes
"""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tenant import Tenant

logger = logging.getLogger("significia.bridge")


# ── Constants ──────────────────────────────────────────────────────
BRIDGE_TIMEOUT_SECONDS = 30
BRIDGE_MAX_RETRIES = 2


class BridgeClient:
    """
    A client for communicating with a specific tenant's Bridge.
    
    Usage:
        bridge = BridgeClient(tenant)
        clients = await bridge.get("/clients")
        result = await bridge.post("/risk-profile/assess", payload)
    """

    def __init__(self, tenant: Tenant):
        if not tenant.bridge_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bridge not configured for this tenant"
            )
        if tenant.bridge_status not in ("ACTIVE", "REGISTERED"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Bridge is {tenant.bridge_status}. Please contact your administrator."
            )

        self.tenant_id = tenant.id
        self.tenant_name = tenant.name
        self.base_url = tenant.bridge_url.rstrip("/")
        self.api_secret = tenant.bridge_api_secret or ""

    def _headers(self) -> Dict[str, str]:
        """Build authentication headers for Bridge requests."""
        return {
            "Authorization": f"Bearer {self.api_secret}",
            "X-Significia-Tenant-Id": str(self.tenant_id),
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: Optional[Dict] = None) -> Any:
        """Send a GET request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge GET] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.get(url, headers=self._headers(), params=params)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                logger.error(f"[Bridge TIMEOUT] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                logger.error(f"[Bridge OFFLINE] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def post(self, path: str, data: Any = None) -> Any:
        """Send a POST request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge POST] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, headers=self._headers(), json=data)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                logger.error(f"[Bridge TIMEOUT] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                logger.error(f"[Bridge OFFLINE] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def patch(self, path: str, data: Any = None) -> Any:
        """Send a PATCH request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge PATCH] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.patch(url, headers=self._headers(), json=data)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def delete(self, path: str) -> Any:
        """Send a DELETE request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge DELETE] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.delete(url, headers=self._headers())
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def upload_file(self, path: str, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> Any:
        """Upload a file to the Bridge (which stores it in the IA's own bucket)."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge UPLOAD] tenant={self.tenant_name} path={path} file={filename}")

        headers = {
            "Authorization": f"Bearer {self.api_secret}",
            "X-Significia-Tenant-Id": str(self.tenant_id),
        }

        async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for uploads
            try:
                files = {"file": (filename, file_bytes, content_type)}
                response = await client.post(url, headers=headers, files=files)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge upload timed out. Please try again.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Cannot upload files.")

    async def health_check(self) -> Dict[str, Any]:
        """Check if the Bridge is alive and responding."""
        try:
            result = await self.get("/health")
            return {"status": "online", **result}
        except HTTPException:
            return {"status": "offline", "bridge_url": self.base_url}

    def _handle_response(self, response: httpx.Response, path: str) -> Any:
        """Process Bridge response, raise appropriate errors."""
        if response.status_code == 200 or response.status_code == 201:
            return response.json()

        if response.status_code == 403:
            logger.warning(f"[Bridge 403] tenant={self.tenant_name} path={path}")
            try:
                detail = response.json().get("detail", "Access denied by Bridge")
            except Exception:
                detail = "Access denied by Bridge"
            raise HTTPException(403, detail)

        if response.status_code == 404:
            try:
                detail = response.json().get("detail", "Not found")
            except Exception:
                detail = "Resource not found on Bridge"
            raise HTTPException(404, detail)

        if response.status_code == 422:
            try:
                detail = response.json().get("detail", "Validation error")
            except Exception:
                detail = "Validation error on Bridge"
            raise HTTPException(422, detail)

        # Unexpected error
        logger.error(
            f"[Bridge ERROR] tenant={self.tenant_name} path={path} "
            f"status={response.status_code} body={response.text[:200]}"
        )
        raise HTTPException(502, f"Bridge returned unexpected status: {response.status_code}")


# ── Helper: Get Bridge Client from Tenant ──────────────────────────
def get_bridge_for_tenant(db: Session, tenant: Tenant) -> BridgeClient:
    """
    Factory function to create a BridgeClient for a given tenant.
    Used as a FastAPI dependency.
    """
    return BridgeClient(tenant)
