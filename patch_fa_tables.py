
import uuid
from app.database.session import SessionLocal
from app.models.connector import Connector
from app.services.provisioner_service import ProvisionerService
from app.connectors.database.postgresql import PostgreSQLConnector
from app.utils.encryption import decrypt_string

def run_migration():
    db = SessionLocal()
    try:
        connectors = db.query(Connector).all()
        for connector in connectors:
            print(f"Patching connector: {connector.name} ({connector.id})")
            try:
                password = decrypt_string(connector.encrypted_password)
                config = {
                    "host": connector.host,
                    "port": connector.port,
                    "database_name": connector.database_name,
                    "username": connector.username,
                    "password": password
                }
                if connector.type == "postgresql":
                    engine = PostgreSQLConnector(config)
                    ProvisionerService._patch_database(engine)
                    print(f"Successfully patched {connector.name}")
            except Exception as e:
                print(f"Failed to patch {connector.name}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
