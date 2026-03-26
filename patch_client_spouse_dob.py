import uuid
from sqlalchemy import create_url, text
from sqlalchemy.orm import Session
import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.database.session import engine, SessionLocal
from app.models.tenant import Tenant

def patch_tenant_databases():
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        print(f"Found {len(tenants)} tenants to patch.")
        
        for tenant in tenants:
            print(f"Patching tenant: {tenant.name} ({tenant.connector_id})")
            
            # Create connection for this tenant
            tenant_url = create_url(tenant.database_url)
            from sqlalchemy import create_engine
            tenant_engine = create_engine(tenant_url)
            
            with tenant_engine.connect() as conn:
                # Add spouse_dob to clients table if not exists
                try:
                    conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS spouse_dob DATE"))
                    conn.commit()
                    print(f"  - Added spouse_dob to clients table.")
                except Exception as e:
                    print(f"  - Error updating clients table: {e}")
                
    except Exception as e:
        print(f"Error during patching: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    patch_tenant_databases()
