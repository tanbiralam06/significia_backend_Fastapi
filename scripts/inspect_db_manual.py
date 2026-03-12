import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.utils.encryption import decrypt_string
from app.database.session import SessionLocal
from app.models.connector import Connector
from app.models.client import ClientProfile
from app.services.client_service import ClientService

def check_remote_db(connector_id):
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
        
        # Test 1: Raw SQL
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM clients"))
            count = result.scalar()
            print(f"Raw SQL count: {count}")
            
            result = conn.execute(text("SELECT id, client_name FROM clients LIMIT 1"))
            row = result.fetchone()
            print(f"Raw SQL example: {row}")

            # Get list of tables and check for 'clients'
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema IN ('significia_core', 'public')"))
            tables = [row[0] for row in result.fetchall()]
            
            if 'clients' in tables:
                print("'clients' table found")
                # List all columns
                result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'clients' AND table_schema IN ('significia_core', 'public')"))
                columns = [row[0] for row in result.fetchall()]
                print(f"COLUMNS IN 'clients': {columns}")
            else:
                print("'clients' table NOT found")

        # Test 2: SQLAlchemy Session + Model
        RemoteSession = sessionmaker(bind=engine)
        session = RemoteSession()
        try:
            print("Querying via Session and ClientProfile model...")
            count = session.query(ClientProfile).count()
            print(f"Model query count: {count}")
            
            print("Calling ClientService.list_clients(session)...")
            clients = ClientService.list_clients(session)
            print(f"Service returned {len(clients)} clients.")
            
            if clients:
                c = clients[0]
                print(f"Example from service: ID={c.id}, Name={c.client_name}")
                
                # Test 3: Serialization
                from app.schemas.client_schema import ClientResponse
                try:
                    resp = ClientResponse.model_validate(c)
                    print("Serialization SUCCESSful")
                except Exception as ser_e:
                    print(f"Serialization FAILED: {ser_e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"SQLAlchemy query failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            session.close()

    except Exception as e:
        print(f"Top level error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_remote_db("bfeb4d39-1c18-41ef-8485-a5ff42e576b2")
