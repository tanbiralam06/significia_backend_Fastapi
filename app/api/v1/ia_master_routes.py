import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.database.remote_session import get_remote_session
from app.schemas.ia_master import IAMasterRead, IANumberValidationResponse, IAMasterPermitUpdate, IAMasterListResponse
from app.services.ia_master_service import IAMasterService
from app.models.user import User

router = APIRouter()
ia_service = IAMasterService()

@router.get("/validate-remote/{ia_number}", response_model=IANumberValidationResponse)
def validate_ia_number_remote(
    ia_number: str,
    db: Session = Depends(get_remote_session)
):
    exists = ia_service.validate_ia_number(db, ia_number)
    return {"exists": exists}

@router.post("/", response_model=IAMasterRead)
async def create_ia_entry(
    name_of_ia: str = Form(...),
    nature_of_entity: str = Form(...),
    name_of_entity: Optional[str] = Form(None),
    ia_registration_number: str = Form(...),
    date_of_registration: str = Form(...),
    date_of_registration_expiry: str = Form(...),
    registered_address: str = Form(...),
    registered_contact_number: str = Form(...),
    office_contact_number: Optional[str] = Form(None),
    registered_email_id: str = Form(...),
    cin_number: Optional[str] = Form(None),
    bank_account_number: str = Form(...),
    bank_name: str = Form(...),
    bank_branch: str = Form(...),
    ifsc_code: str = Form(...),
    employees_json: str = Form("[]"),
    ia_certificate: Optional[UploadFile] = File(None),
    ia_signature: Optional[UploadFile] = File(None),
    ia_logo: Optional[UploadFile] = File(None),
    employee_certificates: List[UploadFile] = File([]),
    db: Session = Depends(get_remote_session),
    current_user: User = Depends(get_current_user)
):
    try:
        ia_data = {
            "name_of_ia": name_of_ia,
            "nature_of_entity": nature_of_entity,
            "name_of_entity": name_of_entity,
            "ia_registration_number": ia_registration_number,
            "date_of_registration": date_of_registration,
            "date_of_registration_expiry": date_of_registration_expiry,
            "registered_address": registered_address,
            "registered_contact_number": registered_contact_number,
            "office_contact_number": office_contact_number,
            "registered_email_id": registered_email_id,
            "cin_number": cin_number,
            "bank_account_number": bank_account_number,
            "bank_name": bank_name,
            "bank_branch": bank_branch,
            "ifsc_code": ifsc_code
        }
        employees_data = json.loads(employees_json)
        db_ia = await ia_service.create_ia_entry(
            db=db, ia_data=ia_data, employees_data=employees_data,
            ia_cert=ia_certificate, ia_sig=ia_signature, ia_logo=ia_logo,
            employee_certs=employee_certificates, tenant_id=current_user.tenant_id
        )
        await ia_service.sign_file_urls(db_ia, db)
        return db_ia
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{ia_id}", response_model=IAMasterRead)
async def update_ia_entry(
    ia_id: uuid.UUID,
    name_of_ia: str = Form(None),
    nature_of_entity: str = Form(None),
    name_of_entity: Optional[str] = Form(None),
    ia_registration_number: str = Form(None),
    date_of_registration: str = Form(None),
    date_of_registration_expiry: str = Form(None),
    registered_address: str = Form(None),
    registered_contact_number: str = Form(None),
    office_contact_number: Optional[str] = Form(None),
    registered_email_id: str = Form(None),
    cin_number: Optional[str] = Form(None),
    bank_account_number: str = Form(None),
    bank_name: str = Form(None),
    bank_branch: str = Form(None),
    ifsc_code: str = Form(None),
    employees_json: str = Form("[]"),
    ia_certificate: Optional[UploadFile] = File(None),
    ia_signature: Optional[UploadFile] = File(None),
    ia_logo: Optional[UploadFile] = File(None),
    employee_certificates: List[UploadFile] = File([]),
    db: Session = Depends(get_remote_session),
    current_user: User = Depends(get_current_user)
):
    try:
        ia_data = {
            k: v for k, v in {
                "name_of_ia": name_of_ia, "nature_of_entity": nature_of_entity,
                "name_of_entity": name_of_entity, "ia_registration_number": ia_registration_number,
                "date_of_registration": date_of_registration, "date_of_registration_expiry": date_of_registration_expiry,
                "registered_address": registered_address, "registered_contact_number": registered_contact_number,
                "office_contact_number": office_contact_number, "registered_email_id": registered_email_id,
                "cin_number": cin_number, "bank_account_number": bank_account_number,
                "bank_name": bank_name, "bank_branch": bank_branch, "ifsc_code": ifsc_code
            }.items() if v is not None
        }
        employees_data = json.loads(employees_json)
        db_ia = await ia_service.update_ia_entry(
            db=db, ia_id=ia_id, ia_data=ia_data, employees_data=employees_data,
            ia_cert=ia_certificate, ia_sig=ia_signature, ia_logo=ia_logo,
            employee_certs=employee_certificates
        )
        await ia_service.sign_file_urls(db_ia, db)
        return db_ia
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{ia_id}/client-permit", response_model=IAMasterRead)
async def update_client_permit(
    ia_id: uuid.UUID,
    permit_update: IAMasterPermitUpdate,
    db: Session = Depends(get_remote_session),
    current_user: User = Depends(get_current_user)
):
    try:
        db_ia = ia_service.update_client_permit(db, ia_id, permit_update.max_client_permit)
        await ia_service.sign_file_urls(db_ia, db)
        return db_ia
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/latest", response_model=Optional[IAMasterRead])
async def get_latest_ia(db: Session = Depends(get_remote_session), current_user: User = Depends(get_current_user)):
    return await ia_service.get_latest_ia(db)

@router.get("/list", response_model=IAMasterListResponse)
async def get_all_ias(skip: int = 0, limit: int = 100, db: Session = Depends(get_remote_session), current_user: User = Depends(get_current_user)):
    return await ia_service.get_all_ias(db, skip=skip, limit=limit)

@router.get("/{ia_id}/pdf")
async def download_ia_pdf(ia_id: uuid.UUID, db: Session = Depends(get_remote_session)):
    try:
        pdf_bytes, filename = await ia_service.generate_pdf(db, ia_id)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
