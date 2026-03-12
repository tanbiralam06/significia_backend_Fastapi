import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.utils.encryption import decrypt_string
from app.database.session import SessionLocal
from app.models.connector import Connector

def migrate_tenant_db(connector_id):
    db = SessionLocal()
    try:
        connector = db.query(Connector).filter(Connector.id == connector_id).first()
        if not connector:
            print("Connector not found")
            return
        
        password = decrypt_string(connector.encrypted_password)
        db_url = f"postgresql+psycopg2://{connector.username}:{password}@{connector.host}:{connector.port}/{connector.database_name}"
        
        print(f"Connecting to: {connector.host}:{connector.port}/{connector.database_name}")
        engine = create_engine(
            db_url,
            connect_args={"options": "-c search_path=significia_core,public"}
        )
        
        with engine.begin() as conn:
            # Check existing columns
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'clients' AND table_schema IN ('significia_core', 'public')"))
            existing_columns = [row[0] for row in result.fetchall()]
            
            columns_to_add = [
                ("advisor_registration_number", "VARCHAR(100) DEFAULT 'NOT_SET' NOT NULL"),
                ("client_date", "DATE DEFAULT CURRENT_DATE NOT NULL"),
                ("previous_advisor_name", "VARCHAR(255)"),
                ("referral_source", "VARCHAR(100)"),
                ("existing_portfolio_value", "FLOAT DEFAULT 0 NOT NULL")
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    print(f"Adding column: {col_name}")
                    conn.execute(text(f"ALTER TABLE clients ADD COLUMN {col_name} {col_type}"))
                else:
                    print(f"Column already exists: {col_name}")
            
            # Also create client_documents and client_audit_trail if they don't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS client_documents (
                    id UUID PRIMARY KEY,
                    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                    document_type VARCHAR(100) NOT NULL,
                    file_path VARCHAR(512) NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            print("Verified/Created client_documents table")

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS client_audit_trail (
                    id UUID PRIMARY KEY,
                    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                    action_type VARCHAR(50) NOT NULL,
                    changes JSONB,
                    user_ip VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            print("Verified/Created client_audit_trail table")

        print("Migration COMPLETED successfully")

    except Exception as e:
        print(f"Migration FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Using the same connector ID as before
    migrate_tenant_db("bfeb4d39-1c18-41ef-8485-a5ff42e576b2")
