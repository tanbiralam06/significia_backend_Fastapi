import sys
import os
from sqlalchemy.orm import Session

# Add the backend directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.models.connector import Connector
from app.services.provisioner_service import ProvisionerService
from app.connectors.database.postgresql import PostgreSQLConnector
from app.utils.encryption import decrypt_string

def migrate_tenants():
    db: Session = SessionLocal()
    try:
        connectors = db.query(Connector).filter(Connector.initialization_status == "READY").all()
        print(f"Found {len(connectors)} connectors to patch.")
        
        for connector in connectors:
            print(f"Patching database for tenant: {connector.name} (ID: {connector.id})")
            if connector.type == "postgresql":
                try:
                    password = decrypt_string(connector.encrypted_password)
                    config = {
                        "host": connector.host,
                        "port": connector.port,
                        "database_name": connector.database_name,
                        "username": connector.username,
                        "password": password
                    }
                    engine = PostgreSQLConnector(config)
                    
                    # Call the patch method from ProvisionerService
                    ProvisionerService._patch_database(engine)
                    print(f"Successfully patched {connector.name}")
                except Exception as e:
                    print(f"Failed to patch {connector.name}: {e}")
            else:
                print(f"Skipping connector type: {connector.type} (Not supported for automatic patching)")
                
    finally:
        db.close()

if __name__ == "__main__":
    migrate_tenants()
