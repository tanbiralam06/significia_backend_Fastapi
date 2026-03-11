from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_client_db, get_tenant_by_slug, get_current_client
from app.models.tenant import Tenant
from app.schemas.client_schema import ClientLoginRequest, ClientTokenResponse, ClientResponse
from app.services.client_auth_service import ClientAuthService
from app.models.client import ClientProfile

router = APIRouter()
client_auth_service = ClientAuthService()

@router.post("/login", response_model=ClientTokenResponse)
def login(
    request: ClientLoginRequest, 
    tenant: Tenant = Depends(get_tenant_by_slug),
    client_db: Session = Depends(get_client_db)
):
    """
    Login endpoint specifically for clients.
    Relies on X-Tenant-Slug header via dependencies to route to correct DB.
    """
    return client_auth_service.authenticate_client(client_db, request, tenant)

@router.get("/me", response_model=ClientResponse)
def get_client_me(current_client: ClientProfile = Depends(get_current_client)):
    return current_client
