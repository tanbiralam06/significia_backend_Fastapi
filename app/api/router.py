from fastapi import APIRouter
from app.api.v1 import (
    auth_routes, client_auth_routes, admin_routes, connector_routes, 
    client_routes, ia_master_routes, storage_routes, api_key_routes,
    financial_analysis_routes
)

api_router = APIRouter()

api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(api_key_routes.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(client_auth_routes.router, prefix="/client-auth", tags=["Client Authentication"])
api_router.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])
api_router.include_router(connector_routes.router, prefix="/connectors", tags=["Database Connectors"])
api_router.include_router(client_routes.router, prefix="/master", tags=["Master Data - Clients"])
api_router.include_router(ia_master_routes.router, prefix="/ia-master", tags=["Master Data - Investment Advisor"])
api_router.include_router(storage_routes.router, prefix="/storage", tags=["Storage Connectors"])
api_router.include_router(financial_analysis_routes.router, prefix="/financial-analysis", tags=["Financial Analysis"])

@api_router.get("/health", status_code=200)
def health_check() -> dict:
    """
    Root API health check endpoint.
    """
    return {"status": "ok", "message": "Significia API is running."}
