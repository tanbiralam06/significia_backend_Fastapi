import uuid
import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.repositories.ia_master_repository import IAMasterRepository
from app.repositories.audit_trail_repository import AuditTrailRepository
from app.utils.file_storage import save_upload_file
from app.utils.file_utils import resolve_logo_to_local_path
from app.utils.pdf_generator import IAPDFGenerator
from app.schemas.ia_master import IAMasterCreate, EmployeeCreate
from app.services.bridge_client import BridgeClient
from app.utils.encryption import decrypt_string

class IAMasterService:
    def __init__(self):
        self.ia_repo = IAMasterRepository()
        self.audit_repo = AuditTrailRepository()

    def validate_ia_number(self, db: Session, ia_number: str) -> bool:
        return self.ia_repo.exists_by_reg_number(db, ia_number)

    async def _handle_files(self, ia_data: dict, ia_name: str, ia_cert, ia_sig, ia_logo, db: Session):
        folder_path = f"IA Master/{ia_name}"
        if ia_cert:
            ia_data['ia_certificate_path'] = await save_upload_file(ia_cert, folder_path, "ia_cert", db=db)
        if ia_sig:
            ia_data['ia_signature_path'] = await save_upload_file(ia_sig, folder_path, "ia_sig", db=db)
        if ia_logo:
            ia_data['ia_logo_path'] = await save_upload_file(ia_logo, folder_path, "ia_logo", db=db)

    async def _handle_employees(self, db: Session, db_ia_id: uuid.UUID, employees_data: List[dict], employee_certs: List[UploadFile], ia_name: str):
        from app.models.ia_master import EmployeeDetails
        # Clear old employees to re-sync
        db.query(EmployeeDetails).filter(EmployeeDetails.ia_master_id == db_ia_id).delete()
        
        for i, emp_data in enumerate(employees_data):
            emp_data['ia_master_id'] = db_ia_id
            if i < len(employee_certs) and employee_certs[i]:
                partner_path = f"IA Master/{ia_name}/Partners/{emp_data['name_of_employee']}"
                emp_data['certificate_path'] = await save_upload_file(employee_certs[i], partner_path, f"emp_cert_{i}", db=db)
            self.ia_repo.create_employee(db, emp_data)

    async def create_ia_entry(
        self, 
        db: Session, 
        ia_data: dict, 
        employees_data: List[dict],
        ia_cert: Optional[UploadFile],
        ia_sig: Optional[UploadFile],
        ia_logo: Optional[UploadFile],
        employee_certs: List[Optional[UploadFile]],
        tenant_id: Optional[uuid.UUID] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        from app.models.ia_master import IAMaster
        existing_ia = db.query(IAMaster).filter(IAMaster.ia_registration_number == ia_data['ia_registration_number']).first()

        ia_name = ia_data['name_of_ia']
        await self._handle_files(ia_data, ia_name, ia_cert, ia_sig, ia_logo, db)

        if existing_ia:
            for key, value in ia_data.items():
                if value is not None:
                    setattr(existing_ia, key, value)
            db_ia = existing_ia
            db.commit()
            db.refresh(db_ia)
            action = "UPDATE"
        else:
            db_ia = self.ia_repo.create(db, ia_data)
            action = "INSERT"
        
        await self._handle_employees(db, db_ia.id, employees_data, employee_certs, ia_name)

        changes = f"{'Updated' if action == 'UPDATE' else 'Created'} IA Master: {ia_data['name_of_ia']} (Reg No: {ia_data['ia_registration_number']})"
        self.audit_repo.log_event(db, action, "ia_master", str(db_ia.id), changes=changes, user_ip=user_ip, user_agent=user_agent)
        return db_ia

    async def update_ia_entry(
        self,
        db: Session,
        ia_id: uuid.UUID,
        ia_data: dict,
        employees_data: List[dict],
        ia_cert: Optional[UploadFile],
        ia_sig: Optional[UploadFile],
        ia_logo: Optional[UploadFile],
        employee_certs: List[Optional[UploadFile]],
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        db_ia = self.ia_repo.get_by_id(db, ia_id)
        if not db_ia:
            raise ValueError("IA record not found")

        ia_name = ia_data.get('name_of_ia', db_ia.name_of_ia)
        await self._handle_files(ia_data, ia_name, ia_cert, ia_sig, ia_logo, db)

        for key, value in ia_data.items():
            if value is not None:
                setattr(db_ia, key, value)
        
        db.commit()
        db.refresh(db_ia)
        
        await self._handle_employees(db, db_ia.id, employees_data, employee_certs, ia_name)

        self.audit_repo.log_event(
            db, "UPDATE", "ia_master", str(db_ia.id), 
            changes=f"Updated IA Master (ID: {ia_id}) by ID", 
            user_ip=user_ip, user_agent=user_agent
        )
        return db_ia

    async def sign_file_urls(self, ia_record: any, db: Session):
        if not ia_record:
            return ia_record
        
        async def get_url(path: str):
            if not path:
                return None
            return path
            
        if hasattr(ia_record, 'ia_certificate_path'):
            ia_record.ia_certificate_path = await get_url(ia_record.ia_certificate_path)
        if hasattr(ia_record, 'ia_signature_path'):
            ia_record.ia_signature_path = await get_url(ia_record.ia_signature_path)
        if hasattr(ia_record, 'ia_logo_path'):
            ia_record.ia_logo_path = await get_url(ia_record.ia_logo_path)
        if hasattr(ia_record, 'employees'):
            for emp in ia_record.employees:
                emp.certificate_path = await get_url(emp.certificate_path)
        return ia_record

    async def get_latest_ia(self, db: Session):
        db_ia = self.ia_repo.get_latest(db)
        if db_ia:
            self.audit_repo.log_event(db, "VIEW", "ia_master", str(db_ia.id), f"Viewed IA Master ID: {db_ia.id}")
            await self.sign_file_urls(db_ia, db)
        return db_ia

    async def get_all_ias(self, db: Session, skip: int = 0, limit: int = 100) -> dict:
        total_count = self.ia_repo.get_count(db)
        ias = self.ia_repo.get_all(db, skip=skip, limit=limit)
        for ia in ias:
            await self.sign_file_urls(ia, db)
        self.audit_repo.log_event(db, "VIEW", "ia_master", "ALL", f"Viewed IA Master list (skip={skip}, limit={limit})")
        return {"items": ias, "total_count": total_count}

    def update_client_permit(self, db: Session, ia_id: uuid.UUID, max_permit: int):
        db_ia = self.ia_repo.get_by_id(db, ia_id)
        if not db_ia:
            raise ValueError("IA record not found")
        if max_permit < db_ia.current_client_count:
            raise ValueError(f"Cannot set max permit below current count ({db_ia.current_client_count})")
        old_permit = db_ia.max_client_permit
        db_ia.max_client_permit = max_permit
        db.commit()
        db.refresh(db_ia)
        self.audit_repo.log_event(db, "UPDATE", "ia_master", str(db_ia.id), f"Updated max client permit from {old_permit} to {max_permit}")
        return db_ia

    async def generate_pdf(self, db: Session, ia_id: uuid.UUID) -> Tuple[bytes, str]:
        db_ia = self.ia_repo.get_by_id(db, ia_id)
        if not db_ia:
            raise ValueError("IA record not found")
        employees = self.ia_repo.get_employees_by_master_id(db, ia_id)
        ia_dict = {c.name: getattr(db_ia, c.name) for c in db_ia.__table__.columns}
        ia_dict["name_of_ia"] = decrypt_string(ia_dict.get("name_of_ia"))
        ia_dict["name_of_entity"] = decrypt_string(ia_dict.get("name_of_entity"))
        
        emp_list = [{c.name: getattr(emp, c.name) for c in emp.__table__.columns} for emp in employees]
        logo_path = await resolve_logo_to_local_path(db_ia.ia_logo_path, db)
        pdf_bytes = IAPDFGenerator.generate_ia_report(ia_dict, emp_list, logo_path=logo_path)
        filename = f"IA_Master_Entry_{db_ia.ia_registration_number}.pdf"
        self.audit_repo.log_event(db, "PDF_EXPORT", "ia_master", str(db_ia.id), f"Exported PDF for IA Master ID: {db_ia.id}")
        return pdf_bytes, filename

    async def generate_pdf_bridge(self, db: Session, bridge: BridgeClient) -> Tuple[bytes, str]:
        """
        Fetch IA Master and Employee data from Bridge and generate PDF report.
        Handles logo resolution by getting a pre-signed URL from Bridge storage.
        """
        # 1. Fetch unified IA Master Data (includes employees)
        ia_data = await bridge.get("/ia-master")
        if not ia_data:
            raise ValueError("IA Master data not found on Bridge")
            
        ia_data["name_of_ia"] = decrypt_string(ia_data.get("name_of_ia"))
        ia_data["name_of_entity"] = decrypt_string(ia_data.get("name_of_entity"))

        employees = ia_data.get("employees", [])
        
        # 2. Resolve IA Logo Path (Bridge stores it, Backend needs to download/resolve it for PDF)
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                # Ask Bridge for a temporary signed URL for the logo
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                signed_url = url_resp.get("url")
                if signed_url:
                    logo_path = await resolve_logo_to_local_path(signed_url, db)
            except Exception as e:
                import logging
                logging.getLogger("significia.ia_master").warning(f"Failed to resolve logo for PDF: {e}")

        # 3. Generate PDF using the existing layout
        pdf_bytes = IAPDFGenerator.generate_ia_report(ia_data, employees, logo_path=logo_path)
        
        # 4. Success Audit & Filename
        reg_no = ia_data.get("ia_registration_number", "REPORT")
        filename = f"IA_Master_Report_{reg_no}.pdf"
        
        # Cleanup temp file if it was created by resolve_logo_to_local_path
        # (Though resolve_logo_to_local_path usually handles it if needed or keeps it for cache)
        
        return pdf_bytes, filename
