import sys
import os

# Add the backend path to sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

from app.database.session import SessionLocal
from app.models.connector import Connector
from app.services.provisioner_service import ProvisionerService

def apply_migrations():
    """
    Triggers initialization/patching for all existing connectors to ensure tables 
    (including the new custom risk assessment tables) are created.
    """
    db = SessionLocal()
    try:
        connectors = db.query(Connector).all()
        if not connectors:
            print("No connectors found to patch.")
            return

        print(f"Found {len(connectors)} connectors. Starting migration patch...")
        for c in connectors:
            print(f"Patching connector '{c.name}' (ID: {c.id}, Tenant: {c.tenant_id})...")
            # ProvisionerService.initialize_database calls _patch_database
            success = ProvisionerService.initialize_database(db, c.id, c.tenant_id)
            if success:
                print(f"Successfully patched {c.name}.")
            else:
                print(f"FAILED to patch {c.name}. Check ProvisionerService logs.")
        
        print("Migration process completed.")
    except Exception as e:
        print(f"An error occurred during migrations: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    apply_migrations()
