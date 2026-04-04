"""
IA Master Routes — Bridge Architecture
───────────────────────────────────────
IA Master data operations now go through the Bridge.
"""
import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import Response

from app.api.deps import get_bridge_client, get_current_tenant, get_db
from sqlalchemy.orm import Session
from app.services.bridge_client import BridgeClient
from app.models.tenant import Tenant

# Legacy schemas kept for typed responses
from app.schemas.ia_master import IAMasterRead, IANumberValidationResponse, IAMasterPermitUpdate, IAMasterListResponse

router = APIRouter()

@router.get("/validate/{ia_number}", response_model=IANumberValidationResponse)
async def validate_ia_number_remote(
    ia_number: str,
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy validation to the Bridge silo."""
    return await bridge.get(f"/ia-master/validate/{ia_number}")

@router.post("/", response_model=dict)
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
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Forward IA Registration to the local Bridge service.
    All data and files stay in the IA's local silo.
    """
    try:
        # 1. Prepare Form Data
        data = {
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
            "ifsc_code": ifsc_code,
            "employees_json": employees_json
        }

        # 2. Prepare Files
        files = {}
        if ia_certificate:
            files["ia_certificate"] = (ia_certificate.filename, await ia_certificate.read(), ia_certificate.content_type)
        if ia_signature:
            files["ia_signature"] = (ia_signature.filename, await ia_signature.read(), ia_signature.content_type)
        if ia_logo:
            files["ia_logo"] = (ia_logo.filename, await ia_logo.read(), ia_logo.content_type)
        
        # Note: employee_certificates handling could be added if needed on Bridge side
        
        # 3. Forward to Bridge
        response = await bridge.post_multipart("/ia-master", data=data, files=files)

        # 4. Success check and Tenant state update
        if response:
            check_and_update_profile_completion(db, tenant, response)
            response["is_profile_completed"] = tenant.is_profile_completed
                
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge Registration Failed: {str(e)}")

@router.patch("/{ia_id}", response_model=dict)
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
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Update IA Registration via the Bridge.
    Proxies to the same Bridge logic as POST.
    """
    try:
        # 1. Prepare Form Data (only including non-None values)
        data = {
            k: v for k, v in {
                "name_of_ia": name_of_ia, "nature_of_entity": nature_of_entity,
                "name_of_entity": name_of_entity, "ia_registration_number": ia_registration_number,
                "date_of_registration": date_of_registration, "date_of_registration_expiry": date_of_registration_expiry,
                "registered_address": registered_address, "registered_contact_number": registered_contact_number,
                "office_contact_number": office_contact_number, "registered_email_id": registered_email_id,
                "cin_number": cin_number, "bank_account_number": bank_account_number,
                "bank_name": bank_name, "bank_branch": bank_branch, "ifsc_code": ifsc_code,
                "employees_json": employees_json
            }.items() if v is not None
        }

        # 2. Prepare Files
        files = {}
        if ia_certificate:
            files["ia_certificate"] = (ia_certificate.filename, await ia_certificate.read(), ia_certificate.content_type)
        if ia_signature:
            files["ia_signature"] = (ia_signature.filename, await ia_signature.read(), ia_signature.content_type)
        if ia_logo:
            files["ia_logo"] = (ia_logo.filename, await ia_logo.read(), ia_logo.content_type)
        
        # 3. Forward to Bridge
        response = await bridge.post_multipart("/ia-master", data=data, files=files)

        # 4. Success check and Tenant state update
        mandatory_fields = ["ia_registration_number", "registered_address", "bank_account_number", "ifsc_code"]
        
        # 4. Process response and update completion status
        if response:
            check_and_update_profile_completion(db, tenant, response)
            response["is_profile_completed"] = tenant.is_profile_completed
            
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge Update Failed: {str(e)}")

@router.get("/latest", response_model=dict)
async def get_latest_ia(
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy Latest IA Info request to the Bridge."""
    return await bridge.get("/ia-master")

@router.get("/list", response_model=dict)
async def get_all_ias(
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy List IAs request to the Bridge (usually just returns the owner)."""
    return await bridge.get("/ia-master")

@router.get("/{ia_id}/pdf")
async def download_ia_pdf(
    ia_id: uuid.UUID, 
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy PDF download to the Bridge (if implemented on Bridge side)."""
    raise HTTPException(status_code=501, detail="Bridge PDF generation not yet implemented")
