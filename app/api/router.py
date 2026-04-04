from fastapi import APIRouter, Depends
from app.api.deps import require_profile_completed
from app.api.v1 import (
    auth_routes, client_auth_routes, admin_routes, 
    client_routes, ia_master_routes,
    financial_analysis_routes, risk_profile_routes, asset_allocation_routes,
    bridge_routes, ia_auth_routes, billing_routes, public_routes, tenant_routes
)

api_router = APIRouter()

# ── Public Routes (Discovery) ───────────────────────────────────────
api_router.include_router(public_routes.router, prefix="/public", tags=["Public Branding"])

# ── Core Auth ───────────────────────────────────────────────────────
api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(client_auth_routes.router, prefix="/client-auth", tags=["Client Authentication"])
api_router.include_router(ia_auth_routes.router, prefix="/ia-auth", tags=["IA Staff Authentication"])

# ── Super Admin ─────────────────────────────────────────────────────
api_router.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])
api_router.include_router(billing_routes.router, prefix="/billing", tags=["Billing"])

# ── Bridge Architecture ─────────────────────────────────────────────
api_router.include_router(bridge_routes.router, prefix="/bridge", tags=["Bridge Management"])
api_router.include_router(tenant_routes.router, prefix="/tenants", tags=["Tenant Management"])

# ── Data Routes (Bridge + Legacy) ───────────────────────────────────
api_router.include_router(client_routes.router, prefix="/master", tags=["Master Data - Clients"], dependencies=[Depends(require_profile_completed)])
api_router.include_router(ia_master_routes.router, prefix="/ia-master", tags=["Master Data - Investment Advisor"])
api_router.include_router(financial_analysis_routes.router, prefix="/financial-analysis", tags=["Financial Analysis"], dependencies=[Depends(require_profile_completed)])
api_router.include_router(risk_profile_routes.router, prefix="/risk-profile", tags=["Risk Profile"], dependencies=[Depends(require_profile_completed)])
api_router.include_router(asset_allocation_routes.router, prefix="/asset-allocation", tags=["Asset Allocation"], dependencies=[Depends(require_profile_completed)])

@api_router.get("/health", status_code=200)
def health_check() -> dict:
    """
    Root API health check endpoint.
    """
    return {"status": "ok", "message": "Significia API is running."}

