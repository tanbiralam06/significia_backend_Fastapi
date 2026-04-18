import uuid
from sqlalchemy.orm import Session
from app.models.tenant import Tenant

class TenantRepository:
    def get_by_id(self, db: Session, tenant_id: uuid.UUID) -> Tenant:
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def create(self, db: Session, name: str, subdomain: str = None, **kwargs) -> Tenant:
        if subdomain:
            # If subdomain is provided, ensure it's unique
            base_subdomain = subdomain
            counter = 1
            while db.query(Tenant).filter(Tenant.subdomain == subdomain).first():
                subdomain = f"{base_subdomain}{counter}"
                counter += 1
        
        # Always generate a bridge registration token for new tenants
        registration_token = Tenant.generate_bridge_token()

        db_tenant = Tenant(
            name=name, 
            subdomain=subdomain,
            bridge_registration_token=registration_token,
            bridge_status="PENDING",
            **kwargs
        )
        db.add(db_tenant)
        return db_tenant
