import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.client_schema import ClientLoginRequest, ClientTokenResponse
from app.models.client import ClientProfile
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.core.config import settings
from app.models.tenant import Tenant

class ClientAuthService:
    def authenticate_client(
        self, 
        client_db: Session, 
        request: ClientLoginRequest, 
        tenant: Tenant
    ) -> ClientTokenResponse:
        client = client_db.query(ClientProfile).filter(
            ClientProfile.email_normalized == request.email.lower()
        ).first()
        
        if not client or not verify_password(request.password, client.password_hash):
            if client:
                client.failed_login_attempts += 1
                client_db.commit()
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        if not client.is_active:
            raise HTTPException(status_code=403, detail="Client account is disabled")

        # Generate token restricted to 'client' role and specific tenant
        access_token = create_access_token(
            subject=str(client.id), 
            tenant_id=str(tenant.id), 
            role="client"
        )

        client.last_login_at = datetime.utcnow()
        client.failed_login_attempts = 0
        client_db.commit()

        return ClientTokenResponse(access_token=access_token)
