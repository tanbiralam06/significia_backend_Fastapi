import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import SessionLocal
from app.models.connector import Connector
from app.utils.encryption import decrypt_string

def fix_dbs():
    db = SessionLocal()
    connectors = db.query(Connector).filter(Connector.type == "postgresql", Connector.is_active == True, Connector.initialization_status == "READY").all()
    
    # Try older style generic connectors too
    if not connectors:
        connectors = db.query(Connector).filter(Connector.is_active == True, Connector.initialization_status == "READY").all()

        
    for connector in connectors:
        try:
            password = decrypt_string(connector.encrypted_password)
            db_url = f"postgresql+psycopg://{connector.username}:{password}@{connector.host}:{connector.port}/{connector.database_name}"
            engine = create_engine(db_url)
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE significia_core.ia_master ADD COLUMN max_client_permit INTEGER DEFAULT 10;"))
                    conn.commit()
                except Exception as e:
                    print(f"Column max_client_permit might already exist or error: {e}")
                
                try:
                    conn.execute(text("ALTER TABLE significia_core.ia_master ADD COLUMN current_client_count INTEGER DEFAULT 0;"))
                    conn.commit()
                except Exception as e:
                    print(f"Column current_client_count might already exist or error: {e}")
            print(f"Fixed connector {connector.id}")
        except Exception as e:
            print(f"Failed to fix connector {connector.id}: {e}")
            
    db.close()

if __name__ == "__main__":
    from sqlalchemy import text
    fix_dbs()
