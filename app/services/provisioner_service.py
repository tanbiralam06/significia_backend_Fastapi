import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from app.utils.encryption import decrypt_string
from app.connectors.database.postgresql import PostgreSQLConnector

class ProvisionerService:
    @staticmethod
    def initialize_database(db: Session, config: dict, tenant_id: uuid.UUID) -> bool:

        try:
            if config.get("type") == "postgresql":
                engine = PostgreSQLConnector(config)
                
                # 1. Create Schema
                engine.execute_query("CREATE SCHEMA IF NOT EXISTS significia_core;")
                
                # 2. Set search path for subsequent queries
                # Note: For simple connections, we can prefix the table names
                
                # 3. Create Tables
                ProvisionerService._create_master_tables(engine)
                
                # 4. Patch existing tables (Migration)
                ProvisionerService._patch_database(engine)
                
                return True
            
            return False
        except Exception as e:
            print(f"Provisioning failed: {e}")
            return False

    @staticmethod
    def _patch_database(engine: PostgreSQLConnector):
        """
        Add any missing columns to existing tables for backward compatibility.
        """
        # Add record_version_control_statement to financial_analysis_profiles
        patch_fa_profiles = """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_schema='significia_core' 
                           AND table_name='financial_analysis_profiles' 
                           AND column_name='record_version_control_statement') THEN
                ALTER TABLE significia_core.financial_analysis_profiles 
                ADD COLUMN record_version_control_statement TEXT;
            END IF;
        END $$;
        """
        engine.execute_query(patch_fa_profiles)

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
            spouse_dob DATE,
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
            advisor_registration_number VARCHAR(100) NOT NULL,
            client_date DATE NOT NULL DEFAULT CURRENT_DATE,
            nominee_name VARCHAR(255),
            nominee_relationship VARCHAR(100),
            previous_advisor_name VARCHAR(255),
            referral_source VARCHAR(100),
            declaration_signed BOOLEAN DEFAULT FALSE,
            agreement_date DATE,
            client_signature_path VARCHAR(512),
            advisor_signature_path VARCHAR(512),
            
            assigned_employee_id UUID REFERENCES significia_core.employee_details(id) ON DELETE SET NULL,
            
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
            
            tenant_id UUID,
            is_renewal BOOLEAN DEFAULT FALSE,
            renewal_certificate_no VARCHAR(100),
            renewal_expiry_date DATE,
            relationship_manager_id UUID,
            
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
            date_of_birth DATE NOT NULL,
            date_of_registration DATE,
            date_of_registration_expiry DATE,
            certificate_path VARCHAR(512),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_employee_details)

        # Create Contact Persons Table
        create_contact_persons = """
        CREATE TABLE IF NOT EXISTS significia_core.contact_persons (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ia_master_id UUID NOT NULL REFERENCES significia_core.ia_master(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            designation VARCHAR(100),
            phone_number VARCHAR(20) NOT NULL,
            email VARCHAR(255) NOT NULL,
            address TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_contact_persons)

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

        # Create Financial Analysis Profiles Table
        create_fa_profiles = """
        CREATE TABLE IF NOT EXISTS significia_core.financial_analysis_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,

            pan VARCHAR(20),
            contact VARCHAR(20),
            email VARCHAR(100),
            occupation VARCHAR(100) NOT NULL,
            dob DATE NOT NULL,
            annual_income DOUBLE PRECISION NOT NULL,

            spouse_name VARCHAR(255),
            spouse_dob DATE,
            spouse_occupation VARCHAR(100),

            children JSONB DEFAULT '[]'::jsonb,
            expenses JSONB NOT NULL,
            assets JSONB NOT NULL,
            liabilities JSONB NOT NULL,
            insurance JSONB NOT NULL,
            assumptions JSONB NOT NULL,

            medical_bonus_years DOUBLE PRECISION DEFAULT 0.0,
            medical_bonus_percentage DOUBLE PRECISION DEFAULT 0.0,
            education_investment_pct DOUBLE PRECISION DEFAULT 0.0,
            marriage_investment_pct DOUBLE PRECISION DEFAULT 0.0,

            exclude_ai BOOLEAN DEFAULT FALSE,
            disclaimer_text TEXT,
            discussion_notes TEXT,
            record_version_control_statement TEXT,

            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fa_profiles_client ON significia_core.financial_analysis_profiles(client_id);
        """
        engine.execute_query(create_fa_profiles)

        # Create Financial Analysis Results Table
        create_fa_results = """
        CREATE TABLE IF NOT EXISTS significia_core.financial_analysis_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            profile_id UUID NOT NULL REFERENCES significia_core.financial_analysis_profiles(id) ON DELETE CASCADE,
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,

            calculations JSONB NOT NULL,
            hlv_data JSONB NOT NULL,
            medical_data JSONB NOT NULL,
            cash_flow_analysis JSONB,
            ai_analysis JSONB,

            financial_health_score INTEGER DEFAULT 0,

            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fa_results_profile ON significia_core.financial_analysis_results(profile_id);
        CREATE INDEX IF NOT EXISTS idx_fa_results_client ON significia_core.financial_analysis_results(client_id);
        """
        engine.execute_query(create_fa_results)

        # Create Risk Profile Assessment Table
        create_risk_assessments = """
        CREATE TABLE IF NOT EXISTS significia_core.risk_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            q1_interest_choice VARCHAR(10) NOT NULL,
            q2_importance_factors JSONB NOT NULL,
            q3_probability_bet VARCHAR(10) NOT NULL,
            q4_portfolio_choice VARCHAR(10) NOT NULL,
            q5_loss_behavior VARCHAR(10) NOT NULL,
            q6_market_reaction VARCHAR(10) NOT NULL,
            q7_fund_selection VARCHAR(10) NOT NULL,
            q8_experience_level VARCHAR(10) NOT NULL,
            q9_time_horizon VARCHAR(10) NOT NULL,
            q10_net_worth VARCHAR(10) NOT NULL,
            q11_age_range VARCHAR(10) NOT NULL,
            q12_income_range VARCHAR(10) NOT NULL,
            q13_expense_range VARCHAR(10) NOT NULL,
            q14_dependents VARCHAR(10) NOT NULL,
            q15_active_loan VARCHAR(10) NOT NULL,
            q16_investment_objective VARCHAR(10) NOT NULL,
            calculated_score INTEGER NOT NULL,
            assigned_risk_tier VARCHAR(100) NOT NULL,
            tier_recommendation TEXT,
            disclaimer_text TEXT,
            discussion_notes TEXT,
            question_scores JSONB NOT NULL,
            assessment_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            form_name VARCHAR(255) DEFAULT 'Sample',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_risk_assessments_client ON significia_core.risk_assessments(client_id);
        """
        engine.execute_query(create_risk_assessments)

        # Create Client Risk Master Table
        create_client_risk_master = """
        CREATE TABLE IF NOT EXISTS significia_core.client_risk_master (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            ia_registration_number VARCHAR(100) NOT NULL,
            category_name VARCHAR(100) NOT NULL,
            portfolio_name VARCHAR(100) NOT NULL,
            submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_client_risk_master_client ON significia_core.client_risk_master(client_id);
        """
        engine.execute_query(create_client_risk_master)

        # Create Risk Questionnaire Table (With Disclaimer)
        create_risk_questionnaires = """
        CREATE TABLE IF NOT EXISTS significia_core.risk_questionnaires (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portfolio_name VARCHAR(255) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'draft',
            questions JSONB NOT NULL DEFAULT '[]'::jsonb,
            categories JSONB NOT NULL DEFAULT '[]'::jsonb,
            max_possible_score DOUBLE PRECISION DEFAULT 0.0,
            disclaimer TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        engine.execute_query(create_risk_questionnaires)

        # Create Custom Risk Assessment Table
        create_custom_risk_assessments = """
        CREATE TABLE IF NOT EXISTS significia_core.custom_risk_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            questionnaire_id UUID NOT NULL REFERENCES significia_core.risk_questionnaires(id) ON DELETE CASCADE,
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            responses JSONB NOT NULL,
            total_score DOUBLE PRECISION NOT NULL,
            category_name VARCHAR(100),
            discussion_notes TEXT,
            submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_custom_risk_assessments_q ON significia_core.custom_risk_assessments(questionnaire_id);
        CREATE INDEX IF NOT EXISTS idx_custom_risk_assessments_client ON significia_core.custom_risk_assessments(client_id);
        """
        engine.execute_query(create_custom_risk_assessments)

        # Create Asset Allocation Table
        create_asset_allocations = """
        CREATE TABLE IF NOT EXISTS significia_core.asset_allocations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
            ia_registration_number VARCHAR(100) NOT NULL,
            assigned_risk_tier VARCHAR(100) NOT NULL,
            tier_recommendation TEXT NOT NULL,
            equities_percentage DOUBLE PRECISION DEFAULT 0.0,
            debt_securities_percentage DOUBLE PRECISION DEFAULT 0.0,
            commodities_percentage DOUBLE PRECISION DEFAULT 0.0,
            stocks_percentage DOUBLE PRECISION DEFAULT 0.0,
            mutual_fund_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
            ulip_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
            fixed_deposits_bonds_percentage DOUBLE PRECISION DEFAULT 0.0,
            mutual_fund_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
            ulip_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
            gold_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
            silver_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
            system_conclusion TEXT,
            generate_system_conclusion BOOLEAN DEFAULT TRUE,
            discussion_notes TEXT,
            disclaimer_text TEXT,
            total_allocation DOUBLE PRECISION DEFAULT 100.0,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_asset_allocations_client ON significia_core.asset_allocations(client_id);
        """
        engine.execute_query(create_asset_allocations)
