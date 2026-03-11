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

        # Create Clients Table
        create_clients = """
        CREATE TABLE IF NOT EXISTS significia_core.clients (
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
        engine.execute_query(create_clients)
        
        # Create IA Master Table
        create_ia_master = """
        CREATE TABLE IF NOT EXISTS significia_core.ia_master (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name_of_ia VARCHAR(255) NOT NULL,
            nature_of_entity VARCHAR(50) NOT NULL,
            name_of_entity VARCHAR(255),
            ia_registration_number VARCHAR(100) UNIQUE NOT NULL,
            date_of_registration DATE,
            date_of_registration_expiry DATE,
            registered_address TEXT,
            registered_contact_number VARCHAR(20),
            office_contact_number VARCHAR(20),
            registered_email_id VARCHAR(255),
            cin_number VARCHAR(100),
            bank_account_number VARCHAR(50),
            bank_name VARCHAR(255),
            bank_branch VARCHAR(255),
            ifsc_code VARCHAR(20),
            ia_certificate_path VARCHAR(512),
            ia_signature_path VARCHAR(512),
            ia_logo_path VARCHAR(512),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_ia_master)

        # Create Employee Details Table
        create_employee_details = """
        CREATE TABLE IF NOT EXISTS significia_core.employee_details (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ia_master_id UUID NOT NULL REFERENCES significia_core.ia_master(id) ON DELETE CASCADE,
            name_of_employee VARCHAR(255) NOT NULL,
            designation VARCHAR(100),
            ia_registration_number VARCHAR(100) NOT NULL,
            date_of_registration DATE,
            date_of_registration_expiry DATE,
            certificate_path VARCHAR(512),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_employee_details)

        # Create Storage Connectors Table
        create_storage = """
        CREATE TABLE IF NOT EXISTS significia_core.storage_connectors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            name VARCHAR(255) NOT NULL,
            provider VARCHAR(50) NOT NULL DEFAULT 'S3',
            bucket_name VARCHAR(255) NOT NULL,
            region VARCHAR(100),
            endpoint_url VARCHAR(255),
            access_key_id VARCHAR(255),
            encrypted_secret_key TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            status VARCHAR(50) DEFAULT 'PENDING',
            verified_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_storage)

        # Create Audit Trail Table
        create_audit = """
        CREATE TABLE IF NOT EXISTS significia_core.audit_trail (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            action_type VARCHAR(50) NOT NULL,
            table_name VARCHAR(100) NOT NULL,
            record_id VARCHAR(100) NOT NULL,
            changes TEXT,
            user_ip VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_audit)
