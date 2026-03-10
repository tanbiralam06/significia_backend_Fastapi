import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.connector import Connector
from app.schemas.connector_schema import ConnectorCreate, ConnectorUpdate
from app.utils.encryption import encrypt_string, decrypt_string
from app.connectors.database.postgresql import PostgreSQLConnector

class ConnectorService:
    @staticmethod
    def create_connector(db: Session, tenant_id: uuid.UUID, connector_in: ConnectorCreate) -> Connector:
        encrypted_password = encrypt_string(connector_in.password)
        db_connector = Connector(
            **connector_in.model_dump(exclude={"password"}),
            tenant_id=tenant_id,
            encrypted_password=encrypted_password
        )
        db.add(db_connector)
        db.commit()
        db.refresh(db_connector)
        return db_connector

    @staticmethod
    def get_connector(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Connector]:
        return db.query(Connector).filter(
            Connector.id == connector_id, 
            Connector.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_connectors(db: Session, tenant_id: uuid.UUID) -> List[Connector]:
        return db.query(Connector).filter(Connector.tenant_id == tenant_id).all()

    @staticmethod
    def update_connector(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID, connector_in: ConnectorUpdate) -> Optional[Connector]:
        db_connector = ConnectorService.get_connector(db, connector_id, tenant_id)
        if not db_connector:
            return None
        
        update_data = connector_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["encrypted_password"] = encrypt_string(update_data.pop("password"))
            
        for key, value in update_data.items():
            setattr(db_connector, key, value)
            
        db.commit()
        db.refresh(db_connector)
        return db_connector

    @staticmethod
    def delete_connector(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        db_connector = ConnectorService.get_connector(db, connector_id, tenant_id)
        if not db_connector:
            return False
        db.delete(db_connector)
        db.commit()
        return True

    @staticmethod
    def test_connection(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        db_connector = ConnectorService.get_connector(db, connector_id, tenant_id)
        if not db_connector:
            return False
        
        password = decrypt_string(db_connector.encrypted_password)
        config = {
            "host": db_connector.host,
            "port": db_connector.port,
            "database_name": db_connector.database_name,
            "username": db_connector.username,
            "password": password
        }
        
        if db_connector.type == "postgresql":
            connector = PostgreSQLConnector(config)
            return connector.test_connection()
        
        # Add support for other types here
        return False
