import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.connector import Connector
from app.utils.encryption import decrypt_string
from app.connectors.database.postgresql import PostgreSQLConnector

class ProvisionerService:
    @staticmethod
    def initialize_database(db: Session, connector_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        connector_record = db.query(Connector).filter(
            Connector.id == connector_id,
            Connector.tenant_id == tenant_id
        ).first()

        if not connector_record:
            return False

        connector_record.initialization_status = "INITIALIZING"
        db.commit()

        try:
            password = decrypt_string(connector_record.encrypted_password)
            config = {
                "host": connector_record.host,
                "port": connector_record.port,
                "database_name": connector_record.database_name,
                "username": connector_record.username,
                "password": password
            }

            if connector_record.type == "postgresql":
                engine = PostgreSQLConnector(config)
                
                # 1. Create Schema
                engine.execute_query("CREATE SCHEMA IF NOT EXISTS significia_core;")
                
                # 2. Set search path for subsequent queries
                # Note: For simple connections, we can prefix the table names
                
                # 3. Create Tables
                ProvisionerService._create_master_tables(engine)
                
                connector_record.initialization_status = "READY"
                connector_record.initialized_at = datetime.utcnow()
                db.commit()
                return True
            
            return False
        except Exception as e:
            print(f"Provisioning failed: {e}")
            connector_record.initialization_status = "FAILED"
            db.commit()
            return False

    @staticmethod
    def _create_master_tables(engine: PostgreSQLConnector):
        # 0. Ensure UUID extension exists
        engine.execute_query("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        # Create Customers Table
        create_customers = """
        CREATE TABLE IF NOT EXISTS significia_core.customers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_customers)
        
        # Create Audit Log Table (Generic)
        create_audit = """
        CREATE TABLE IF NOT EXISTS significia_core.audit_logs (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(100),
            record_id UUID,
            action VARCHAR(50),
            old_value JSONB,
            new_value JSONB,
            changed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_audit)
