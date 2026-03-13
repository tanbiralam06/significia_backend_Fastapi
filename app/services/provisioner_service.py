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
                
                # 4. Patch existing tables (Migration)
                ProvisionerService._patch_database(engine)
                
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
    def _patch_database(engine: PostgreSQLConnector):
        """
        Add any missing columns to existing tables for backward compatibility.
        """
        try:
            # Add deleted_at to clients if missing
            engine.execute_query("ALTER TABLE significia_core.clients ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE;")
            # Add aadhar and passport numbers
            engine.execute_query("ALTER TABLE significia_core.clients ADD COLUMN IF NOT EXISTS aadhar_number VARCHAR(12);")
            engine.execute_query("ALTER TABLE significia_core.clients ADD COLUMN IF NOT EXISTS passport_number VARCHAR(50);")
            # Add date_of_birth to relevant tables
            engine.execute_query("ALTER TABLE significia_core.ia_master ADD COLUMN IF NOT EXISTS date_of_birth DATE;")
            engine.execute_query("ALTER TABLE significia_core.employee_details ADD COLUMN IF NOT EXISTS date_of_birth DATE;")
        except Exception as e:
            print(f"Migration patching failed: {e}")

    @staticmethod
    def _create_master_tables(engine: PostgreSQLConnector):
        # 0. Ensure UUID extension exists
        engine.execute_query("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        # Create Clients Table
        create_clients = """
        CREATE TABLE IF NOT EXISTS significia_core.clients (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            email_normalized VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            failed_login_attempts INTEGER DEFAULT 0,
            last_login_at TIMESTAMP WITHOUT TIME ZONE,
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            
            client_code VARCHAR(50) UNIQUE NOT NULL,
            client_name VARCHAR(255) NOT NULL,
            date_of_birth DATE NOT NULL,
            pan_number VARCHAR(20) UNIQUE NOT NULL,
            phone_number VARCHAR(50) NOT NULL,
            address TEXT NOT NULL,
            occupation VARCHAR(100) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            marital_status VARCHAR(50) NOT NULL,
            nationality VARCHAR(100) NOT NULL,
            residential_status VARCHAR(100) NOT NULL,
            tax_residency VARCHAR(100) NOT NULL,
            pep_status VARCHAR(100) NOT NULL,
            father_name VARCHAR(255) NOT NULL,
            mother_name VARCHAR(255) NOT NULL,
            spouse_name VARCHAR(255),
            aadhar_number VARCHAR(12),
            passport_number VARCHAR(50),
            
            annual_income DOUBLE PRECISION NOT NULL,
            net_worth DOUBLE PRECISION NOT NULL,
            income_source VARCHAR(100) NOT NULL,
            fatca_compliance VARCHAR(100) NOT NULL,
            existing_portfolio_value DOUBLE PRECISION DEFAULT 0.0,
            existing_portfolio_composition TEXT,
            
            bank_account_number VARCHAR(50) NOT NULL,
            bank_name VARCHAR(255) NOT NULL,
            bank_branch VARCHAR(255) NOT NULL,
            ifsc_code VARCHAR(20) NOT NULL,
            demat_account_number VARCHAR(100),
            trading_account_number VARCHAR(100),
            
            risk_profile VARCHAR(100) NOT NULL,
            investment_experience VARCHAR(100) NOT NULL,
            investment_objectives TEXT NOT NULL,
            investment_horizon VARCHAR(100) NOT NULL,
            liquidity_needs VARCHAR(100) NOT NULL,
            
            advisor_name VARCHAR(255) NOT NULL,
            nominee_name VARCHAR(255),
            nominee_relationship VARCHAR(100),
            declaration_signed BOOLEAN DEFAULT FALSE,
            declaration_date DATE,
            client_signature_path VARCHAR(512),
            advisor_signature_path VARCHAR(512),
            
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_clients_email_normalized ON significia_core.clients(email_normalized);
        """
        engine.execute_query(create_clients)

        # Create Client Documents Table
        create_client_docs = """
        CREATE TABLE IF NOT EXISTS significia_core.client_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            document_type VARCHAR(100) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            uploaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_client_docs)

        # Create Client Audit Trail Table
        create_client_audit = """
        CREATE TABLE IF NOT EXISTS significia_core.client_audit_trail (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            action_type VARCHAR(50) NOT NULL,
            changes JSONB,
            user_ip VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_client_audit)
        
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
            max_client_permit INTEGER DEFAULT 10,
            current_client_count INTEGER DEFAULT 0,
            date_of_birth DATE,
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
            date_of_birth DATE,
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
