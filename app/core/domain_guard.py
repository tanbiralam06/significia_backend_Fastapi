"""
Domain-Based Login Guard Middleware
───────────────────────────────────
Enforces role-based access based on the request origin:

  app.significia.com  →  Only Significia Super Admins can access
  bunty.com           →  Only IA staff and clients of that tenant
  localhost           →  Dev mode — all access allowed

This is a critical SEBI compliance component:
  - IA staff should NEVER see the Super Admin dashboard
  - Super Admins should NEVER accidentally access IA panels
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("significia.domain_guard")

# Routes that are always public (no domain guard)
PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/bridge/register",
    "/api/v1/bridge/heartbeat",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Routes restricted to Super Admin origin (app.significia.com)
SUPER_ADMIN_PREFIXES = [
    "/api/v1/admin/",
    "/api/v1/bridge/tenants/",
    "/api/v1/bridge/initialize-tenant/",
]

# Significia's own domains (Super Admin access)
SIGNIFICIA_DOMAINS = [
    "app.significia.com",
    "api.significia.com",
    "significia.com",
    "www.significia.com",
    "localhost",      # Dev mode
    "127.0.0.1",
    "103.176.85.73",  # Production VPS IP
]


class DomainGuardMiddleware(BaseHTTPMiddleware):
    """
    Middleware that checks the request's Host header and blocks
    unauthorized access based on domain + route combination.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        host = (request.headers.get("host", "") or "").split(":")[0].lower()

        # Always allow public paths
        if path in PUBLIC_PATHS or path.rstrip("/") in PUBLIC_PATHS:
            return await call_next(request)

        # Always allow health checks and static files
        if path.startswith("/static") or path == "/favicon.ico":
            return await call_next(request)

        # Check: Super Admin routes should only be accessible from Significia domains
        is_super_admin_route = any(path.startswith(prefix) for prefix in SUPER_ADMIN_PREFIXES)
        is_significia_domain = host in SIGNIFICIA_DOMAINS

        if is_super_admin_route and not is_significia_domain:
            logger.warning(
                f"[DOMAIN GUARD] Blocked Super Admin route access from IA domain. "
                f"host={host} path={path}"
            )
            raise HTTPException(
                status_code=403,
                detail="This route is restricted to the Significia admin portal."
            )

        # For Bridge-powered routes accessed from IA domains:
        # The get_current_tenant dependency will handle tenant validation
        # No additional blocking needed here — the dependency chain handles it

        return await call_next(request)
