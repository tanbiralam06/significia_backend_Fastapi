from app.api.v1 import auth_routes, admin_routes, connector_routes

api_router = APIRouter()

api_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])
api_router.include_router(connector_routes.router, prefix="/connectors", tags=["Database Connectors"])

@api_router.get("/health", status_code=200)
def health_check() -> dict:
    """
    Root API health check endpoint.
    """
    return {"status": "ok", "message": "Significia API is running."}
