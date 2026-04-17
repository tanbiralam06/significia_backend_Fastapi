import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.api.deps import get_db, get_current_user, get_bridge_client
from app.services.rectification_service import RectificationService
from app.schemas.data_rectification_schema import RectificationCreate, RectificationResponse, PaginatedRectificationResponse
from app.services.bridge_client import BridgeClient
from app.models.user import User
from app.models.staff_profile import StaffProfile
from app.models.ia_master import IAMaster
from sqlalchemy import select
from app.utils.reports.rectification_report import RectificationPDFGenerator

router = APIRouter()

async def enrich_rectifications_with_names(rectifications: List[dict], db: Session) -> List[dict]:
    """Helper to attach names and roles to rectification dicts, prioritizing Bridge data."""
    user_ids = []
    for r in rectifications:
        for key in ["requested_by_id", "approved_by_id"]:
            rid = r.get(key)
            if rid:
                try:
                    uid = uuid.UUID(str(rid))
                    if uid not in user_ids:
                        user_ids.append(uid)
                except (ValueError, TypeError):
                    continue
                
    if not user_ids:
        return rectifications
    
    # Fetch User details to check roles and tenant_ids
    stmt_users = select(User.id, User.email, User.role, User.tenant_id).where(User.id.in_(user_ids))
    users_data = db.execute(stmt_users).all()
    user_map = {row.id: {"email": row.email, "role": row.role, "tenant_id": row.tenant_id} for row in users_data}
    
    # Fetch Staff Profiles
    stmt_profiles = select(StaffProfile.user_id, StaffProfile.full_name).where(StaffProfile.user_id.in_(user_ids))
    profiles_data = db.execute(stmt_profiles).all()
    profile_map = {row.user_id: row.full_name for row in profiles_data}
    
    # Fetch IA Master names for IA users
    tenant_ids = {u["tenant_id"] for u in user_map.values() if u["role"] == "IA"}
    ia_map = {}
    if tenant_ids:
        stmt_ia = select(IAMaster.tenant_id, IAMaster.name_of_ia).where(IAMaster.tenant_id.in_(list(tenant_ids)))
        ia_data = db.execute(stmt_ia).all()
        ia_map = {row.tenant_id: row.name_of_ia for row in ia_data}
    
    for r in rectifications:
        # 1. Handle Requested By
        rid = r.get("requested_by_id")
        if not rid:
            r["requested_by_name"] = "Internal Process"
        else:
            uid = uuid.UUID(str(rid))
            user_info = user_map.get(uid)
            
            # Name Logic: Prefer Bridge name if valid
            bridge_name = r.get("requested_by_name")
            if not bridge_name or bridge_name in ["System/Legacy", "admin", "admin@significia.com"]:
                if user_info:
                    name = profile_map.get(uid)
                    if not name and user_info["role"] == "IA":
                        name = ia_map.get(user_info["tenant_id"])
                    if not name:
                        name = user_info["email"].split("@")[0]
                    r["requested_by_name"] = name
            
            # Role Logic: Always attach if we have user info and it's missing
            if user_info and not r.get("requested_by_role"):
                r["requested_by_role"] = user_info["role"]

        # 2. Handle Approved By
        aid = r.get("approved_by_id")
        if aid:
            uid = uuid.UUID(str(aid))
            user_info = user_map.get(uid)
            
            # Name Logic
            bridge_approved_name = r.get("approved_by_name")
            if not bridge_approved_name or bridge_approved_name in ["admin"]:
                if user_info:
                    name = profile_map.get(uid)
                    if not name and user_info["role"] == "IA":
                        name = ia_map.get(user_info["tenant_id"])
                    if not name:
                        name = user_info["email"].split("@")[0]
                    r["approved_by_name"] = name
            
            # Role Logic
            if user_info and not r.get("approved_by_role"):
                r["approved_by_role"] = user_info["role"]
            
    return rectifications




# ... existing code ...

@router.get("/{rectification_id}/pdf")
async def download_rectification_pdf(
    rectification_id: uuid.UUID,
    db: Session = Depends(get_db),
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Generate and download the Data Rectification Authorization Form as PDF.
    """
    try:
        # 1. Fetch Rectification Data
        rectification = await bridge.get(f"/rectification/{rectification_id}")
        
        # Enrich with staff name
        enriched_list = await enrich_rectifications_with_names([rectification], db)
        rectification = enriched_list[0]

        
        # 2. Fetch Client Data
        client_id = rectification.get("client_id")
        client = await bridge.get(f"/clients/{client_id}")
        
        # 3. Fetch IA Master Data
        stmt_ia = select(IAMaster).where(IAMaster.tenant_id == current_user.tenant_id)
        ia_record = db.execute(stmt_ia).scalar_one_or_none()
        ia_data = {column.name: getattr(ia_record, column.name) for column in ia_record.__table__.columns} if ia_record else {}

        
        # 4. Generate PDF
        pdf_bytes = RectificationPDFGenerator.generate_rectification_form(
            rectification, client, ia_data
        )
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Rectification_{rectification.get('serial_no')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate PDF: {str(e)}")


# Directory for storing signed rectification documents
UPLOAD_DIR = "uploads/rectification_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/current-values/{module}/{record_id}")
async def get_current_values(
    module: str,
    record_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch the latest data for any module to pre-fill the rectification form.
    """
    return await RectificationService.get_current_values(bridge, module, record_id)

@router.post("/initiate", response_model=RectificationResponse)
async def initiate_rectification(
    payload: RectificationCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new rectification process (Status: DRAFT).
    Generates the unique Serial No starting with 'E'.
    """
    return await RectificationService.initiate_rectification(bridge, payload, current_user.id)


@router.get("/list", response_model=PaginatedRectificationResponse)
async def list_rectifications(
    client_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    List rectifications via the Bridge with pagination and search.
    """
    result = await RectificationService.list_rectifications(bridge, client_id, page, limit, search)
    records = result.get("records", [])
    total = result.get("total", 0)
    
    enriched_records = await enrich_rectifications_with_names(records, db)
    
    return {
        "records": enriched_records,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/{rectification_id}", response_model=RectificationResponse)
async def get_rectification(
    rectification_id: uuid.UUID,
    db: Session = Depends(get_db),
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific rectification record.
    """
    record = await bridge.get(f"/rectification/{rectification_id}")
    enriched = await enrich_rectifications_with_names([record], db)
    return enriched[0]


@router.patch("/{rectification_id}", response_model=RectificationResponse)
async def update_rectification(
    rectification_id: uuid.UUID,
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing rectification draft.
    """
    try:
        return await RectificationService.update_rectification(bridge, rectification_id, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{rectification_id}/upload")
async def upload_signed_form(
    rectification_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("signed_form"),
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Upload compliance documents.
    doc_type: 'investor_request' or 'signed_form'
    """
    file_bytes = await file.read()
    try:
        rectification = await RectificationService.upload_signed_document(
            bridge, rectification_id, file_bytes, file.filename, file.content_type, doc_type
        )
        return rectification
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{rectification_id}/approve")
async def approve_rectification(
    rectification_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    IA Final approval of the rectification.
    """
    # Check if user is IA (role check)
    if current_user.role.lower() not in ["owner", "ia", "admin"]:
         raise HTTPException(status_code=403, detail="Only Investment Advisers can approve rectifications")
         
    try:
        return await RectificationService.approve_rectification(bridge, rectification_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{rectification_id}/document")
async def download_rectification_document(
    rectification_id: uuid.UUID,
    doc_type: str = "signed_form",
    filename: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Proxy document download from the Bridge.
    Handles 'investor_request', 'signed_form', and 'proposed_change'.
    """
    # 1. Determine file path
    if doc_type == "proposed_change":
        if not filename:
             raise HTTPException(400, "Filename is required for proposed documents")
        # Fetch record to get client_id (needed for folder structure)
        record = await bridge.get(f"/rectification/{rectification_id}")
        client_id = record.get("client_id")
        file_path = f"/{current_user.tenant_id}/clients/{client_id}/rectification/{rectification_id}/proposed/{filename}"
    else:
        # 1. Get record to find path for compliance docs
        record = await bridge.get(f"/rectification/{rectification_id}")
        col = "investor_request_path" if doc_type == "investor_request" else "signed_form_path"
        file_path = record.get(col)
    
    if not file_path:
        raise HTTPException(404, "Document path not found")
        
    # 2. Fetch from Bridge
    try:
        response = await bridge.get_raw(f"/storage/{file_path.lstrip('/')}")
        if response.status_code != 200:
             raise HTTPException(response.status_code, "Failed to fetch file from Silo")
    except Exception as e:
        logger.error(f"Error proxying file download: {e}")
        raise HTTPException(500, f"Error fetching document: {str(e)}")
    
    return StreamingResponse(
        io.BytesIO(response.content),
        media_type=response.headers.get("Content-Type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"inline; filename={os.path.basename(file_path)}"
        }
    )

@router.delete("/{rectification_id}/document")
async def delete_rectification_document(
    rectification_id: uuid.UUID,
    doc_type: str = "signed_form",
    bridge: BridgeClient = Depends(get_bridge_client),
    current_user: User = Depends(get_current_user)
):
    """
    Proxy document deletion to the Bridge.
    """
    return await bridge.delete(f"/rectification/{rectification_id}/document?doc_type={doc_type}")

