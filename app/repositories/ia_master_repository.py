import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.ia_master import IAMaster, EmployeeDetails, ContactPerson

class IAMasterRepository:
    # ... (existing methods)
    def create_contact_person(self, db: Session, contact_data: dict) -> ContactPerson:
        db_contact = ContactPerson(**contact_data)
        db.add(db_contact)
        return db_contact
    def get_by_id(self, db: Session, ia_id: uuid.UUID) -> Optional[IAMaster]:
        return db.query(IAMaster).filter(IAMaster.id == ia_id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[IAMaster]:
        return db.query(IAMaster).order_by(IAMaster.created_at.desc()).offset(skip).limit(limit).all()

    def get_count(self, db: Session) -> int:
        return db.query(IAMaster).count()

    def get_latest(self, db: Session) -> Optional[IAMaster]:
        return db.query(IAMaster).order_by(IAMaster.id.desc()).first()

    def create(self, db: Session, ia_data: dict) -> IAMaster:
        db_ia = IAMaster(**ia_data)
        db.add(db_ia)
        return db_ia

    def create_employee(self, db: Session, employee_data: dict) -> EmployeeDetails:
        db_employee = EmployeeDetails(**employee_data)
        db.add(db_employee)
        return db_employee

    def exists_by_reg_number(self, db: Session, reg_number: str) -> bool:
        # Check in ia_master
        master_exists = db.query(IAMaster).filter(IAMaster.ia_registration_number == reg_number).first() is not None
        if master_exists:
            return True
        
        # Check in employee_details
        employee_exists = db.query(EmployeeDetails).filter(EmployeeDetails.ia_registration_number == reg_number).first() is not None
        return employee_exists

    def get_employees_by_master_id(self, db: Session, master_id: uuid.UUID) -> List[EmployeeDetails]:
        return db.query(EmployeeDetails).filter(EmployeeDetails.ia_master_id == master_id).all()
