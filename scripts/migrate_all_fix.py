import os
from sqlalchemy import create_engine, text
from app.database.session import SessionLocal
from app.models.connector import Connector
from app.utils.encryption import decrypt_string
from dotenv import load_dotenv

load_dotenv()

def migrate_all():
    db = SessionLocal()
    try:
        connectors = db.query(Connector).all()
        print(f"Found {len(connectors)} connectors.")
        
        for connector in connectors:
            print(f"\n--- Migrating Connector: {connector.name} ({connector.id}) ---")
            try:
                password = decrypt_string(connector.encrypted_password)
                db_url = f"postgresql+psycopg2://{connector.username}:{password}@{connector.host}:{connector.port}/{connector.database_name}"
                
                # Use significia_core schema
                engine = create_engine(db_url, connect_args={"options": "-c search_path=significia_core,public"})
                
                with engine.begin() as conn:
                    # IA Master
                    print("Checking ia_master...")
                    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'ia_master' AND column_name = 'date_of_birth' AND table_schema = 'significia_core'"))
                    if not res.fetchone():
                        print("Adding date_of_birth to ia_master...")
                        conn.execute(text("ALTER TABLE ia_master ADD COLUMN date_of_birth DATE"))
                    
                    conn.execute(text("UPDATE ia_master SET date_of_birth = '1980-01-01' WHERE date_of_birth IS NULL"))
                    conn.execute(text("ALTER TABLE ia_master ALTER COLUMN date_of_birth SET NOT NULL"))

                    # Employee Details
                    print("Checking employee_details...")
                    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'employee_details' AND column_name = 'date_of_birth' AND table_schema = 'significia_core'"))
                    if not res.fetchone():
                        print("Adding date_of_birth to employee_details...")
                        conn.execute(text("ALTER TABLE employee_details ADD COLUMN date_of_birth DATE"))
                    
                    conn.execute(text("UPDATE employee_details SET date_of_birth = '1980-01-01' WHERE date_of_birth IS NULL"))
                    conn.execute(text("ALTER TABLE employee_details ALTER COLUMN date_of_birth SET NOT NULL"))
                    
                    print(f"Successfully migrated {connector.name}")
            except Exception as e:
                print(f"Error migrating {connector.name}: {e}")
                
    except Exception as e:
        print(f"Migration script failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_all()
