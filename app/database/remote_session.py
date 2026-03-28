import uuid
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException
from app.api.deps import get_db, get_current_user, api_key_header, oauth2_scheme
from app.models.connector import Connector
from app.models.user import User
from app.models.api_key import ApiKey
from app.utils.encryption import decrypt_string
import hashlib

def get_remote_session(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Depends(api_key_header)
) -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy session specifically bound to a 
    tenant's private database connector. Supports JWT or X-API-Key auth.
    """
    tenant_id = None
    is_super_admin = False
    
    if x_api_key:
        hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
        api_key_obj = db.query(ApiKey).filter(ApiKey.hashed_key == hashed, ApiKey.is_active == True).first()
        if not api_key_obj:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        tenant_id = api_key_obj.tenant_id
    elif token:
        user = get_current_user(db=db, token=token)
        tenant_id = user.tenant_id
        is_super_admin = user.role == "super_admin"
        
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required (JWT or X-API-Key)")

    if is_super_admin:
        connector = db.query(Connector).filter(Connector.id == connector_id).first()
    else:
        connector = db.query(Connector).filter(
            Connector.id == connector_id,
            Connector.tenant_id == tenant_id
        ).first()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    if connector.initialization_status != "READY":
        raise HTTPException(
            status_code=400, 
            detail="Database not initialized. Please run initialization first."
        )

    try:
        password = decrypt_string(connector.encrypted_password)
        # Construct SQLAlchemy URL
        # For now assuming PostgreSQL
        db_url = f"postgresql+psycopg://{connector.username}:{password}@{connector.host}:{connector.port}/{connector.database_name}"
        
        # Create engine with search path set to our private schema
        engine = create_engine(
            db_url,
            connect_args={"options": "-c search_path=significia_core,public"}
        )
        
        RemoteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to remote database: {str(e)}")

    session = RemoteSessionLocal()
    try:
        yield session
    finally:
        session.close()
