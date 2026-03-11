import uuid
from sqlalchemy.orm import Session
from app.models.tenant import Tenant

class TenantRepository:
    def get_by_id(self, db: Session, tenant_id: uuid.UUID) -> Tenant:
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def create(self, db: Session, name: str, subdomain: str = None) -> Tenant:
        import re
        if not subdomain:
            subdomain = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            
        # Ensure it's unique
        base_subdomain = subdomain
        counter = 1
        while db.query(Tenant).filter(Tenant.subdomain == subdomain).first():
            subdomain = f"{base_subdomain}{counter}"
            counter += 1

        db_tenant = Tenant(name=name, subdomain=subdomain)
        db.add(db_tenant)
        db.commit()
        db.refresh(db_tenant)
        return db_tenant
