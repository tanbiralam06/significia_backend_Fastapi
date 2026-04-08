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
from fastapi.encoders import jsonable_encoder
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

    def __init__(self, tenant: Tenant, user: Optional[Any] = None):
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
        self.base_url = f"{tenant.bridge_url.rstrip('/')}/api/v1/bridge"
        self.api_secret = tenant.bridge_api_secret or ""
        self.user = user

    def _headers(self, skip_content_type: bool = False) -> Dict[str, str]:
        """Build authentication headers for Bridge requests."""
        headers = {
            "Authorization": f"Bearer {self.api_secret}",
            "X-Significia-Tenant-Id": str(self.tenant_id),
        }
        if not skip_content_type:
            headers["Content-Type"] = "application/json"
            
        if self.user:
            headers["X-User-Id"] = str(self.user.id)
            headers["X-User-Role"] = str(self.user.role)
        return headers

    def _merge_headers(self, custom_headers: Optional[Dict[str, str]] = None, skip_content_type: bool = False) -> Dict[str, str]:
        """Merge base headers with optional custom headers."""
        base = self._headers(skip_content_type=skip_content_type)
        if custom_headers:
            base.update(custom_headers)
        return base

    async def get(self, path: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Any:
        """Send a GET request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge GET] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.get(url, headers=self._merge_headers(headers), params=params)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                logger.error(f"[Bridge TIMEOUT] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                logger.error(f"[Bridge OFFLINE] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def post(self, path: str, data: Any = None, headers: Optional[Dict] = None) -> Any:
        """Send a POST request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge POST] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, headers=self._merge_headers(headers), json=jsonable_encoder(data))
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                logger.error(f"[Bridge TIMEOUT] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                logger.error(f"[Bridge OFFLINE] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def put(self, path: str, data: Any = None, headers: Optional[Dict] = None) -> Any:
        """Send a PUT request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge PUT] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.put(url, headers=self._merge_headers(headers), json=jsonable_encoder(data))
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                logger.error(f"[Bridge TIMEOUT] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                logger.error(f"[Bridge OFFLINE] tenant={self.tenant_name} path={path}")
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def patch(self, path: str, data: Any = None, headers: Optional[Dict] = None) -> Any:
        """Send a PATCH request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge PATCH] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.patch(url, headers=self._merge_headers(headers), json=jsonable_encoder(data))
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def delete(self, path: str, headers: Optional[Dict] = None) -> Any:
        """Send a DELETE request to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge DELETE] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT_SECONDS) as client:
            try:
                response = await client.delete(url, headers=self._merge_headers(headers))
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge is not responding. Please try again later.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Please contact your administrator.")

    async def upload_file(
        self, 
        path: str, 
        file_bytes: bytes, 
        filename: str, 
        content_type: str = "application/octet-stream",
        headers: Optional[Dict] = None
    ) -> Any:
        """Upload a single file to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge UPLOAD] tenant={self.tenant_name} path={path} file={filename}")

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                files = {"file": (filename, file_bytes, content_type)}
                response = await client.post(url, headers=self._merge_headers(headers, skip_content_type=True), files=files)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge upload timed out. Please try again.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline. Cannot upload files.")

    async def post_multipart(self, path: str, data: Dict[str, Any], files: Dict[str, Any], headers: Optional[Dict] = None) -> Any:
        """Send a POST request with multiple files and form data to the Bridge."""
        url = f"{self.base_url}{path}"
        logger.info(f"[Bridge MULTIPART] tenant={self.tenant_name} path={path}")

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(url, headers=self._merge_headers(headers, skip_content_type=True), data=data, files=files)
                return self._handle_response(response, path)
            except httpx.ConnectTimeout:
                raise HTTPException(503, "Bridge multipart request timed out.")
            except httpx.ConnectError:
                raise HTTPException(503, "Bridge is offline.")

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

        if response.status_code == 401:
            logger.warning(f"[Bridge 401] tenant={self.tenant_name} path={path}")
            try:
                detail = response.json().get("detail", "Invalid credentials on Bridge")
            except Exception:
                detail = "Invalid credentials on Bridge"
            raise HTTPException(401, detail)

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
            logger.warning(f"[Bridge 422] tenant={self.tenant_name} path={path} body={response.text[:200]}")
            try:
                detail = response.json().get("detail", "Validation error")
            except Exception:
                detail = f"Validation error on Bridge: {response.text}"
            raise HTTPException(422, detail)

        # Unexpected error (5xx or other)
        logger.error(
            f"[Bridge ERROR] tenant={self.tenant_name} path={path} "
            f"status={response.status_code} body={response.text[:200]}"
        )
        # Try to extract the error message from the body if available
        try:
            detail = response.json().get("detail", f"Bridge Error (Status {response.status_code})")
        except Exception:
            detail = f"Bridge returned status {response.status_code}: {response.text[:100]}"
            
        raise HTTPException(response.status_code if response.status_code >= 400 and response.status_code < 600 else 502, detail)


# ── Helper: Get Bridge Client from Tenant ──────────────────────────
def get_bridge_for_tenant(db: Session, tenant: Tenant) -> BridgeClient:
    """
    Factory function to create a BridgeClient for a given tenant.
    Used as a FastAPI dependency.
    """
    return BridgeClient(tenant)
