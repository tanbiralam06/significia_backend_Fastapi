import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.client_schema import ClientCreate, ClientUpdate
from app.models.ia_master import IAMaster
from app.models.client import ClientProfile
from app.core.security import get_password_hash

class ClientService:
    @staticmethod
    def create_client(db: Session, client_in: ClientCreate) -> ClientProfile:
        # Check IA Master Limit
        ia_master = db.query(IAMaster).order_by(IAMaster.created_at.desc()).first()
        if not ia_master:
            raise ValueError("IA Master record must be created before adding clients.")
        
        if ia_master.current_client_count >= ia_master.max_client_permit:
            raise ValueError(f"Maximum client permit ({ia_master.max_client_permit}) reached.")

        # Check existing
        existing = db.query(ClientProfile).filter(
            (ClientProfile.email_normalized == client_in.email.lower()) | 
            (ClientProfile.pan_number == client_in.pan_number)
        ).first()

        if existing:
            raise ValueError("Client with this email or PAN already exists.")

        create_data = client_in.model_dump()
        raw_password = create_data.pop("password")
        
        db_client = ClientProfile(
            **create_data,
            password_hash=get_password_hash(raw_password),
            email_normalized=client_in.email.lower()
        )
        
        db.add(db_client)
        
        # Increment client count
        ia_master.current_client_count += 1
        
        db.commit()
        db.refresh(db_client)
        return db_client

    @staticmethod
    def get_client(db: Session, client_id: uuid.UUID) -> Optional[ClientProfile]:
        return db.query(ClientProfile).filter(ClientProfile.id == client_id).first()

    @staticmethod
    def list_clients(db: Session) -> List[ClientProfile]:
        return db.query(ClientProfile).all()

    @staticmethod
    def update_client(db: Session, client_id: uuid.UUID, client_in: ClientUpdate) -> Optional[ClientProfile]:
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
