import uuid
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate

# We define a separate Base for remote tables to avoid mixing with local metadata
RemoteBase = declarative_base()

class RemoteCustomer(RemoteBase):
    __tablename__ = "customers"
    __table_args__ = {"schema": "significia_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CustomerService:
    @staticmethod
    def create_customer(db: Session, customer_in: CustomerCreate) -> RemoteCustomer:
        db_customer = RemoteCustomer(**customer_in.model_dump())
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def get_customer(db: Session, customer_id: uuid.UUID) -> Optional[RemoteCustomer]:
        return db.query(RemoteCustomer).filter(RemoteCustomer.id == customer_id).first()

    @staticmethod
    def list_customers(db: Session) -> List[RemoteCustomer]:
        return db.query(RemoteCustomer).all()

    @staticmethod
    def update_customer(db: Session, customer_id: uuid.UUID, customer_in: CustomerUpdate) -> Optional[RemoteCustomer]:
        db_customer = CustomerService.get_customer(db, customer_id)
        if not db_customer:
            return None
        
        update_data = customer_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_customer, key, value)
            
        db.commit()
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def delete_customer(db: Session, customer_id: uuid.UUID) -> bool:
        db_customer = CustomerService.get_customer(db, customer_id)
        if not db_customer:
            return False
        db.delete(db_customer)
        db.commit()
        return True
