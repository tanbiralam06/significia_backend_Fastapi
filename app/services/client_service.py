import uuid
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.client_schema import ClientCreate, ClientUpdate
from app.models.ia_master import IAMaster

# We define a separate Base for remote tables to avoid mixing with local metadata
RemoteBase = declarative_base()

class RemoteClient(RemoteBase):
    __tablename__ = "clients"
    __table_args__ = {"schema": "significia_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClientService:
    @staticmethod
    def create_client(db: Session, client_in: ClientCreate) -> RemoteClient:
        # Check IA Master Limit
        ia_master = db.query(IAMaster).order_by(IAMaster.created_at.desc()).first()
        if not ia_master:
            raise ValueError("IA Master record must be created before adding clients.")
        
        if ia_master.current_client_count >= ia_master.max_client_permit:
            raise ValueError(f"Maximum client permit ({ia_master.max_client_permit}) reached.")

        db_client = RemoteClient(**client_in.model_dump())
        db.add(db_client)
        
        # Increment client count
        ia_master.current_client_count += 1
        
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def get_client(db: Session, client_id: uuid.UUID) -> Optional[RemoteClient]:
        return db.query(RemoteClient).filter(RemoteClient.id == client_id).first()

    @staticmethod
    def list_clients(db: Session) -> List[RemoteClient]:
        return db.query(RemoteClient).all()

    @staticmethod
    def update_client(db: Session, client_id: uuid.UUID, client_in: ClientUpdate) -> Optional[RemoteClient]:
        db_client = ClientService.get_client(db, client_id)
        if not db_client:
            return None
        
        update_data = client_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_client, key, value)
            
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def delete_client(db: Session, client_id: uuid.UUID) -> bool:
        db_client = ClientService.get_client(db, client_id)
        if not db_client:
            return False
            
        ia_master = db.query(IAMaster).order_by(IAMaster.created_at.desc()).first()
        if ia_master and ia_master.current_client_count > 0:
            ia_master.current_client_count -= 1
            
        db.delete(db_client)
        db.commit()
        return True
