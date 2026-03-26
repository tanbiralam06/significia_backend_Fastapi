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
    def _log_audit(db: Session, client_id: uuid.UUID, action: str, changes: Optional[dict] = None):
        from app.models.client import ClientAuditTrail
        audit = ClientAuditTrail(
            client_id=client_id,
            action_type=action,
            changes=changes
        )
        db.add(audit)

    @staticmethod
    def generate_next_client_code(db: Session) -> str:
        # Fetch the latest client code manually
        # Expected format: C0000000001
        last_client = db.query(ClientProfile).filter(
            ClientProfile.client_code.like("C%")
        ).order_by(ClientProfile.client_code.desc()).first()
        
        if not last_client:
            return "C0000000001"
            
        try:
            current_num = int(last_client.client_code[1:])
            next_num = current_num + 1
            return f"C{next_num:010d}"
        except (ValueError, TypeError):
            return "C0000000001"

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
            if existing.deleted_at:
                raise ValueError("A deactivated client with this email or PAN already exists.")
            raise ValueError("Client with this email or PAN already exists.")

        create_data = client_in.model_dump()
        raw_password = create_data.pop("password")
        
        # Generate Client Code
        generated_code = ClientService.generate_next_client_code(db)
        
        db_client = ClientProfile(
            **create_data,
            client_code=generated_code,
            password_hash=get_password_hash(raw_password),
            email_normalized=client_in.email.lower()
        )
        
        db.add(db_client)
        
        # Increment client count
        ia_master.current_client_count += 1
        
        db.commit()
        db.refresh(db_client)
        
        ClientService._log_audit(db, db_client.id, "CREATE")
        db.commit()
        
        return db_client

    @staticmethod
    def get_client(db: Session, client_id: uuid.UUID) -> Optional[ClientProfile]:
        return db.query(ClientProfile).filter(
            ClientProfile.id == client_id,
            ClientProfile.deleted_at == None
        ).first()

    @staticmethod
    def get_client_by_pan(db: Session, pan_number: str) -> Optional[ClientProfile]:
        """Fetch client details by PAN number for real-time validation."""
        return db.query(ClientProfile).filter(
            ClientProfile.pan_number == pan_number.upper(),
            ClientProfile.deleted_at == None
        ).first()

    @staticmethod
    def list_clients(db: Session) -> List[ClientProfile]:
        return db.query(ClientProfile).filter(ClientProfile.deleted_at == None).all()

    @staticmethod
    def update_client(db: Session, client_id: uuid.UUID, client_in: ClientUpdate) -> Optional[ClientProfile]:
        db_client = ClientService.get_client(db, client_id)
        if not db_client:
            return None
        
        update_data = client_in.model_dump(exclude_unset=True)
        changes = {}
        for key, value in update_data.items():
            old_val = getattr(db_client, key)
            if old_val != value:
                changes[key] = {"old": str(old_val), "new": str(value)}
                setattr(db_client, key, value)
            
        if changes:
            ClientService._log_audit(db, db_client.id, "UPDATE", changes)
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
            
        # Soft delete
        db_client.is_active = False
        db_client.deleted_at = datetime.utcnow()
        db.commit()
        return True
        
    @staticmethod
    def generate_pdf(db: Session, client_id: uuid.UUID) -> tuple[bytes, str]:
        from app.utils.pdf_generator import ClientPDFGenerator
        db_client = ClientService.get_client(db, client_id)
        if not db_client:
            raise ValueError("Client not found")

        # Convert to dict for generator
        client_dict = {c.name: getattr(db_client, c.name) for c in db_client.__table__.columns}
        
        # Ensure numeric fields are actually numbers and not None
        numeric_fields = ["annual_income", "net_worth", "existing_portfolio_value"]
        for field in numeric_fields:
            if client_dict.get(field) is None:
                client_dict[field] = 0.0
            else:
                client_dict[field] = float(client_dict[field])

        pdf_bytes = ClientPDFGenerator.generate_client_report(client_dict)
        filename = f"Client_Report_{db_client.client_code}_{db_client.client_name.replace(' ', '_')}.pdf"
        
        ClientService._log_audit(db, db_client.id, "PDF_EXPORT")
        db.commit()
        return pdf_bytes, filename

    @staticmethod
    def generate_master_report(db: Session) -> tuple[bytes, str]:
        from app.models.ia_master import EmployeeDetails
        
        # Join query to get client data and assigned employee name
        results = db.query(
            ClientProfile,
            EmployeeDetails.name_of_employee.label("employee_name")
        ).outerjoin(
            EmployeeDetails, ClientProfile.assigned_employee_id == EmployeeDetails.id
        ).filter(ClientProfile.deleted_at == None).all()
        
        clients_data = []
        for client, employee_name in results:
            data = {c.name: getattr(client, c.name) for c in client.__table__.columns}
            data["employee_name"] = employee_name
            clients_data.append(data)
            
        from app.utils.pdf_generator import ClientPDFGenerator
        pdf_bytes = ClientPDFGenerator.generate_client_master_report(clients_data)
        
        filename = f"Client_Master_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf_bytes, filename
