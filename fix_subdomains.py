import re
from app.database.session import SessionLocal
from app.models.tenant import Tenant

def fix_subdomains():
    db = SessionLocal()
    tenants = db.query(Tenant).filter(Tenant.subdomain == None).all()
    
    for tenant in tenants:
        base_subdomain = re.sub(r'[^a-zA-Z0-9]', '', tenant.name).lower()
        if not base_subdomain:
            base_subdomain = "tenant"
            
        subdomain = base_subdomain
        counter = 1
        
        # Check uniqueness against DB and already processed in this script
        while db.query(Tenant).filter(Tenant.subdomain == subdomain).first():
            subdomain = f"{base_subdomain}{counter}"
            counter += 1
            
        tenant.subdomain = subdomain
        db.add(tenant)
        print(f"Set subdomain for {tenant.name} to {subdomain}")
        db.commit()

    db.close()

if __name__ == "__main__":
    fix_subdomains()
