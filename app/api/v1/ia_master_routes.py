"""
IA Master Routes — Bridge Architecture
───────────────────────────────────────
IA Master data operations now go through the Bridge.
"""
import logging
import uuid
import json
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from fastapi.responses import Response

from app.api.deps import get_bridge_client, get_current_tenant, get_db, get_current_user
from sqlalchemy.orm import Session
from app.services.bridge_client import BridgeClient
from app.services.ia_master_service import IAMasterService
from app.models.tenant import Tenant

# Legacy schemas kept for typed responses
from app.schemas.ia_master import IAMasterRead, IANumberValidationResponse, IAMasterPermitUpdate, IAMasterListResponse

logger = logging.getLogger("significia.ia_master")

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
    date_of_birth: Optional[str] = Form(None),
    name_of_entity: Optional[str] = Form(None),
    basl_membership_id: str = Form(...),
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
    ia_certificate: Optional[UploadFile] = File(None),
    ia_signature: Optional[UploadFile] = File(None),
    ia_logo: Optional[UploadFile] = File(None),
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
            "date_of_birth": date_of_birth,
            "nature_of_entity": nature_of_entity,
            "name_of_entity": name_of_entity,
            "basl_membership_id": basl_membership_id,
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
            logger.info(f"Bridge registration successful for tenant {tenant.id}")
            check_and_update_profile_completion(db, tenant, response)
            response["is_profile_completed"] = tenant.is_profile_completed
                
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge Registration Failed: {str(e)}")

@router.patch("/{ia_id}", response_model=dict)
async def update_ia_entry(
    ia_id: uuid.UUID,
    name_of_ia: str = Form(None),
    nature_of_entity: str = Form(None),
    date_of_birth: str = Form(None),
    name_of_entity: Optional[str] = Form(None),
    basl_membership_id: Optional[str] = Form(None),
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
    ia_certificate: Optional[UploadFile] = File(None),
    ia_signature: Optional[UploadFile] = File(None),
    ia_logo: Optional[UploadFile] = File(None),
    change_reason_type: str = Form("data_update"),
    change_reason_text: str = Form("Manual update"),
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    current_user: Any = Depends(get_current_user)
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
                "date_of_birth": date_of_birth,
                "name_of_entity": name_of_entity, 
                "basl_membership_id": basl_membership_id,
                "ia_registration_number": ia_registration_number,
                "date_of_registration": date_of_registration, "date_of_registration_expiry": date_of_registration_expiry,
                "registered_address": registered_address, "registered_contact_number": registered_contact_number,
                "office_contact_number": office_contact_number, "registered_email_id": registered_email_id,
                "cin_number": cin_number, "bank_account_number": bank_account_number,
                "bank_name": bank_name, "bank_branch": bank_branch, "ifsc_code": ifsc_code,
                "editing_user_id": str(current_user.id),
                "change_reason_type": change_reason_type,
                "change_reason_text": change_reason_text,
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
            logger.info(f"Bridge profile update successful for tenant {tenant.id}")
            check_and_update_profile_completion(db, tenant, response)
            response["is_profile_completed"] = tenant.is_profile_completed
            
        return response

    except HTTPException:
        # Re-raise HTTP exceptions from the Bridge directly to the frontend
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge Update Failed: {str(e)}")

@router.get("/latest", response_model=dict)
async def get_latest_ia(
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy Latest IA Info request to the Bridge."""
    return await bridge.get("/ia-master")

@router.get("/employees", response_model=List[dict])
async def list_ia_employees(
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy Team/Employee list request to the Bridge silo."""
    return await bridge.get("/employees")

@router.get("/list", response_model=dict)
async def get_all_ias(
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """Proxy List IAs request to the Bridge (usually just returns the owner)."""
    return await bridge.get("/ia-master")

@router.get("/{ia_id}/pdf")
async def download_ia_pdf(
    ia_id: uuid.UUID, 
    request: Request,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Proxy PDF download to the Bridge (using Backend generator)."""
    try:
        service = IAMasterService()
        pdf_bytes, filename = await service.generate_pdf_bridge(db, bridge)
        
        # --- SEBI AUDIT ---
        await bridge.post("/sebi/audit", {
            "action_type": "EXPORT",
            "table_name": "iamaster",
            "record_id": str(ia_id),
            "change_reason_type": "report_generation",
            "change_reason_text": "IA Master Data PDF Report Exported"
        }, headers={
            "X-User-Id": str(current_user.id),
            "X-User-IP": request.client.host if request.client else "0.0.0.0",
            "X-User-Agent": request.headers.get("User-Agent", "Unknown")
        })

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"IA Master PDF Generation Failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
# ── Helper: Completion Check ──────────────────────────────────────
def check_and_update_profile_completion(db: Session, tenant: Tenant, bridge_data: dict):
    """
    Check if the IA Master profile in the Bridge silo has all mandatory fields.
    If so, mark the tenant's profile as completed in the Master Database.
    """
    mandatory_fields = [
        "ia_registration_number", 
        "registered_address", 
        "bank_account_number", 
        "ifsc_code"
    ]
    
    # Check if all mandatory fields have values (not None or empty string)
    is_complete = True
    missing_fields = []
    
    for field in mandatory_fields:
        val = bridge_data.get(field)
        if val is None or str(val).strip() == "":
            is_complete = False
            missing_fields.append(field)
            
    logger.info(f"[PROFILE COMPLETION] Tenant {tenant.name}: is_complete={is_complete}, missing={missing_fields}")
    
    # Update Tenant completion state if it changed
    if is_complete != tenant.is_profile_completed:
        logger.info(f"[PROFILE COMPLETION] Transitioning tenant {tenant.name} is_profile_completed to {is_complete}")
        tenant.is_profile_completed = is_complete
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return is_complete


# ══════════════════════════════════════════════════════════════════
#  SEBI-SAFE COMPLIANCE — Bridge Proxy Endpoints
# ══════════════════════════════════════════════════════════════════

@router.get("/sebi/audit-trail/export")
async def export_sebi_audit_trail(
    format: str = "csv",
    table_name: str = None,
    record_id: str = None,
    from_date: str = None,
    to_date: str = None,
    request: Request = None,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: Any = Depends(get_current_user),
):
    """
    Export full SEBI audit trail as CSV or JSON.
    Supports date range filtering (from_date, to_date as YYYY-MM-DD)
    and table/record filtering.
    """
    from app.utils.reports.audit_trail_report import AuditTrailReportGenerator

    try:
        # 1. Fetch bulk audit data from Bridge
        params = {}
        if table_name:
            params["table_name"] = table_name
        if record_id:
            params["record_id"] = record_id
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date

        export_data = await bridge.get("/sebi/audit-trail/export", params=params)

        entries = export_data.get("entries", [])
        filters = export_data.get("filters", {})

        # 2. Fetch IA Master metadata for report header
        ia_data = None
        try:
            ia_data = await bridge.get("/ia-master")
        except Exception:
            pass

        # 3. Generate export file
        if format.lower() == "json":
            file_bytes = AuditTrailReportGenerator.generate_json(entries, filters, ia_data)
            media_type = "application/json"
        else:
            file_bytes = AuditTrailReportGenerator.generate_csv(entries, filters, ia_data)
            media_type = "text/csv"

        filename = AuditTrailReportGenerator.get_filename(
            format.lower() if format.lower() in ("csv", "json") else "csv",
            from_date, to_date
        )

        # 4. Audit the export action
        try:
            await bridge.post("/sebi/audit", {
                "action_type": "EXPORT",
                "table_name": "audit_trail",
                "record_id": "bulk_export",
                "change_reason_type": "report_generation",
                "change_reason_text": f"Audit Trail exported as {format.upper()} ({len(entries)} entries)",
            }, headers={
                "X-User-Id": str(current_user.id),
                "X-User-IP": request.client.host if request and request.client else "0.0.0.0",
                "X-User-Agent": request.headers.get("User-Agent", "Unknown") if request else "Unknown",
            })
        except Exception as e:
            logger.warning(f"Failed to log audit export event: {e}")

        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit trail export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export audit trail")


@router.get("/sebi/audit-trail")
async def get_sebi_audit_trail(
    table_name: str = None,
    record_id: str = None,
    limit: int = 100,
    offset: int = 0,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Fetch SEBI-compliant audit trail from the Bridge."""
    params = {"limit": limit, "offset": offset}
    if table_name:
        params["table_name"] = table_name
    if record_id:
        params["record_id"] = record_id
    return await bridge.get("/sebi/audit-trail", params=params)


@router.get("/sebi/ia-master/versions")
async def get_ia_versions(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Retrieve all IA Master version snapshots."""
    return await bridge.get("/sebi/ia-master/versions")


@router.get("/sebi/ia-master/versions/{version_number}")
async def get_ia_version(
    version_number: int,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Get a specific version snapshot."""
    return await bridge.get(f"/sebi/ia-master/versions/{version_number}")


@router.post("/sebi/ia-master/lock")
async def lock_ia_master(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Lock the IA Master record."""
    return await bridge.post("/sebi/ia-master/lock", payload)


@router.post("/sebi/ia-master/unlock")
async def unlock_ia_master(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Unlock the IA Master record (owner only)."""
    return await bridge.post("/sebi/ia-master/unlock", payload)


@router.get("/sebi/report-history")
async def get_report_history(
    client_id: str = None,
    report_type: str = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Retrieve report generation history."""
    params = {}
    if client_id:
        params["client_id"] = client_id
    if report_type:
        params["report_type"] = report_type
    return await bridge.get("/sebi/report-history", params=params)


@router.get("/sebi/report-history/lookup")
async def lookup_report(
    source_record_id: str,
    report_type: str = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Look up the latest report for a specific source record."""
    params = {"source_record_id": source_record_id}
    if report_type:
        params["report_type"] = report_type
    return await bridge.get("/sebi/report-history/lookup", params=params)


@router.post("/sebi/report-history")
async def create_report_history(
    data: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Record a report generation event (Unified Route)."""
    return await bridge.post("/reports/history", data)


@router.post("/sebi/report-history/{report_id}/deliver")
async def redeliver_report_history(
    report_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db)
):
    """
    Stateless RE-DELIVERY of a previously recorded report.
    Fetches history metadata from Bridge, re-generates report on-the-fly,
    and sends via Bridge SMTP relay.
    """
    from app.services.financial_report_service import FinancialReportService
    
    # 1. Fetch the audit record from the Bridge to get profile_id and version
    try:
        audit_record = await bridge.get(f"/reports/history/record/{report_id}")
    except Exception as e:
        logger.error(f"Failed to fetch audit record for re-delivery: {e}")
        raise HTTPException(404, "Report history record not found on Bridge")

    # 2. Trigger re-generation and delivery
    result = await FinancialReportService.redeliver_report_via_bridge(
        bridge=bridge,
        db=db,
        audit_record=audit_record
    )
    
    # Safely check for success/message as result might be a SimpleNamespace
    success = False
    message = None
    if hasattr(result, "get"):
        success = result.get("success", False)
        message = result.get("message")
    else:
        success = getattr(result, "success", False)
        message = getattr(result, "message", None)

    if not success and message:
        raise HTTPException(500, f"Re-delivery failed: {message}")
        
    return result


@router.get("/sebi/ia-master/change-summary")
async def get_change_summary(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Proxy: Get human-readable change summary for IA Master."""
    return await bridge.get("/sebi/ia-master/change-summary")
