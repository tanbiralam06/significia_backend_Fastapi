import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.storage_connector import StorageConnector
from app.utils.encryption import encrypt_string, decrypt_string
from app.connectors.storage.s3_connector import S3Storage
from app.connectors.storage.base_storage import BaseStorage

class StorageService:
    @staticmethod
    def get_tenant_storage(db: Session, tenant_id: Optional[uuid.UUID] = None) -> Optional[BaseStorage]:
        """
        Retrieves the active storage connector from the provided DB session (Client DB).
        """
        try:
            connector_record = db.query(StorageConnector).filter(
                StorageConnector.is_active == True
            ).first()
        except Exception:
            return None

        if not connector_record:
            return None

        # Decrypt secret key
        secret_key = decrypt_string(connector_record.encrypted_secret_key)
        
        config = {
            "provider": connector_record.provider,
            "bucket_name": connector_record.bucket_name,
            "region": connector_record.region,
            "endpoint_url": connector_record.endpoint_url,
            "access_key_id": connector_record.access_key_id,
            "secret_key": secret_key
        }

        if connector_record.provider.upper() == "S3":
            return S3Storage(config)
        
        # Add GCS/Azure implementations here as needed
        return None

    @staticmethod
    def create_storage_connector(db: Session, tenant_id: uuid.UUID, data: Dict[str, Any]) -> StorageConnector:
        # Encrypt the secret key before saving
        if "secret_key" in data:
            data["encrypted_secret_key"] = encrypt_string(data.pop("secret_key"))
        
        db_connector = StorageConnector(
            **data,
            tenant_id=tenant_id
        )
        db.add(db_connector)
        # We don't commit here anymore, let the router handle it
        db.flush() 
        return db_connector

    @staticmethod
    async def test_and_verify_connector(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        connector_record = db.query(StorageConnector).filter(
            StorageConnector.id == connector_id,
            StorageConnector.tenant_id == tenant_id
        ).first()

        if not connector_record:
            return False

        secret_key = decrypt_string(connector_record.encrypted_secret_key)
        config = {
            "bucket_name": connector_record.bucket_name,
            "region": connector_record.region,
            "endpoint_url": connector_record.endpoint_url,
            "access_key_id": connector_record.access_key_id,
            "secret_key": secret_key
        }

        driver = None
        try:
            if connector_record.provider.upper() == "S3":
                driver = S3Storage(config)
        except Exception as e:
            print(f"Driver initialization failed: {e}")
            connector_record.status = "FAILED"
            db.commit()
            return False

        if driver and await driver.test_connection():
            from datetime import datetime
            connector_record.status = "READY"
            connector_record.verified_at = datetime.utcnow()
            return True
        
        connector_record.status = "FAILED"
        return False
