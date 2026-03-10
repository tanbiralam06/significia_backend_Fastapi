import uuid
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException
from app.api.deps import get_db, get_current_user
from app.models.connector import Connector
from app.models.user import User
from app.utils.encryption import decrypt_string

def get_remote_session(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy session specifically bound to a 
    tenant's private database connector.
    """
    connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.tenant_id == current_user.tenant_id
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
        session = RemoteSessionLocal()
        try:
            yield session
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to remote database: {str(e)}")
