from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from datetime import datetime
import json
import io
import asyncio

from app.api.deps import get_bridge_client, get_db
from app.services.bridge_client import BridgeClient
from app.schemas.asset_allocation import AssetAllocationCreate
from app.utils.reports.asset_allocation_report import AssetAllocationReportUtils
from app.utils.encryption import decrypt_string
import logging

router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES (no connector_id)
# ════════════════════════════════════════════════════════════════════

@router.post("/bridge/validate-client", response_model=dict)
async def validate_client_bridge(
    payload: dict,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Validate a client via the Bridge."""
    return await bridge.post("/asset-allocations/validate-client", payload)


@router.post("/bridge/save", response_model=dict)
async def save_asset_allocation_bridge(
    payload: AssetAllocationCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Save an asset allocation via the Bridge."""
    return await bridge.post("/asset-allocations", payload.model_dump())


@router.get("/bridge/allocations", response_model=list)
async def list_allocations_bridge(
    client_id: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """List all asset allocations via the Bridge, optionally filtered by client_id."""
    params = {"client_id": client_id} if client_id else None
    return await bridge.get("/asset-allocations", params=params)



@router.get("/bridge/allocation/{allocation_id}", response_model=dict)
async def get_allocation_bridge(
    allocation_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a specific allocation via the Bridge."""
    return await bridge.get(f"/asset-allocations/{allocation_id}")


@router.get("/bridge/blank-form/pdf")
async def download_blank_form_pdf(
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db)
):
    """Generate and download a blank asset allocation form."""
    try:
        # 1. Fetch IA Master info from Bridge for branding
        ia_data = await bridge.get("/ia-master")
        
        # IA branding details
        ia_name = ia_data.get("name_of_ia") or "____________________________"
        ia_entity = ia_data.get("entity_name") or "____________________________"
        ia_reg_no = ia_data.get("registration_no") or "________________"
        ia_logo_key = ia_data.get("ia_logo_path")
        
        # 2. Resolve Logo from Bridge storage
        logo_path = None
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                signed_url = url_resp.get("url")
                if signed_url:
                    logo_path = await resolve_logo_to_local_path(signed_url, db)
            except: pass

        # 3. Create mock IA object (since we don't have direct DB access to IAMaster)
        class MockIA: pass
        ia = MockIA()
        ia.name_of_ia = ia_name
        ia.name_of_entity = ia_entity
        ia.ia_registration_number = ia_reg_no
        ia.ia_reg_no = ia_reg_no # Support multiple attribute names

        # 4. Generate PDF
        pdf_buffer = AssetAllocationReportUtils.generate_blank_pdf(ia, ia_logo_path=logo_path)
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=Asset_Allocation_Blank_Form.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate blank form: {str(e)}")


@router.get("/bridge/allocation/{allocation_id}/pdf")
async def download_allocation_pdf(
    allocation_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db)
):
    """Generate and download a PDF report for an allocation."""
    try:
        # 1. Fetch allocation and IA data
        import asyncio
        allocation_task = bridge.get(f"/asset-allocations/{allocation_id}")
        ia_task = bridge.get("/ia-master")
        allocation_data, ia_data = await asyncio.gather(allocation_task, ia_task)
        
        # 2. Prepare branding - IA data comes plain from the Bridge
        ia_name = ia_data.get("name_of_ia")
        ia_entity = ia_data.get("entity_name")
        ia_reg_no = ia_data.get("registration_no")
        ia_logo_key = ia_data.get("ia_logo_path")
        
        logo_path = None
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                if url_resp.get("url"):
                    logo_path = await resolve_logo_to_local_path(url_resp["url"], db)
            except: pass

        class MockObject:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    if isinstance(v, dict): setattr(self, k, MockObject(**v))
                    else: setattr(self, k, v)
        
        # Ensure allocation has client object for the report util
        if "client" not in allocation_data:
            allocation_data["client"] = {
                "client_name": allocation_data.get("client_name") or "Client",
                "client_code": allocation_data.get("client_code") or "N/A"
            }
        
        # Convert created_at string to datetime for utility
        if "created_at" in allocation_data and isinstance(allocation_data["created_at"], str):
            try:
                allocation_data["created_at"] = datetime.fromisoformat(allocation_data["created_at"].replace("Z", "+00:00"))
            except:
                allocation_data["created_at"] = datetime.now()

        ia_email = ia_data.get("registered_email_id") or ""
        ia = MockObject(name_of_ia=ia_name, ia_registration_number=ia_reg_no, registered_email_id=ia_email)
        allocation = MockObject(**allocation_data)
        
        # 3. Generate PDF
        pdf_buffer = AssetAllocationReportUtils.generate_pdf(allocation, ia, ia_logo_path=logo_path)
        
        filename = f"Asset_Allocation_{allocation_data.get('client_code') or allocation_id}.pdf"
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridge/allocation/{allocation_id}/docx")
async def download_allocation_docx(
    allocation_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Generate and download a DOCX report for an allocation."""
    try:
        # 1. Fetch data
        import asyncio
        allocation_task = bridge.get(f"/asset-allocations/{allocation_id}")
        ia_task = bridge.get("/ia-master")
        allocation_data, ia_data = await asyncio.gather(allocation_task, ia_task)
        
        # 2. Prepare mock objects - IA data comes plain from the Bridge
        ia_name = ia_data.get("name_of_ia")
        ia_entity = ia_data.get("entity_name")
        ia_reg_no = ia_data.get("registration_no")

        class MockObject:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    if isinstance(v, dict): setattr(self, k, MockObject(**v))
                    else: setattr(self, k, v)
        
        if "client" not in allocation_data:
            allocation_data["client"] = {
                "client_name": allocation_data.get("client_name") or "Client",
                "client_code": allocation_data.get("client_code") or "N/A"
            }
        
        if "created_at" in allocation_data and isinstance(allocation_data["created_at"], str):
            try:
                allocation_data["created_at"] = datetime.fromisoformat(allocation_data["created_at"].replace("Z", "+00:00"))
            except:
                allocation_data["created_at"] = datetime.now()

        ia_email = ia_data.get("registered_email_id") or ""
        ia = MockObject(name_of_ia=ia_name, ia_registration_number=ia_reg_no, registered_email_id=ia_email)
        allocation = MockObject(**allocation_data)
        
        # 3. Generate DOCX
        docx_buffer = AssetAllocationReportUtils.generate_docx(allocation, ia)
        
        filename = f"Asset_Allocation_{allocation_data.get('client_code') or allocation_id}.docx"
        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bridge/allocation/{allocation_id}/email")
async def email_allocation_report(
    allocation_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db)
):
    """Generate and email an asset allocation report via the Bridge."""
    try:
        # 1. Fetch data
        allocation_data = await bridge.get(f"/asset-allocations/{allocation_id}")
        ia_data = await bridge.get("/ia-master")
        
        # 2. Prepare branding & Client info
        client_name = allocation_data.get("client_name") or "Valued Client"
        client_code = allocation_data.get("client_code")
        
        # Resolve client email from Bridge
        client = await bridge.get(f"/clients/code/{client_code}") if client_code else None
        client_email = client.get("email") if client else allocation_data.get("email")
        
        if not client_email:
            raise HTTPException(status_code=400, detail="Client email not found")

        ia_name = ia_data.get("name_of_ia") or ia_data.get("entity_name") or "Your Advisor"
        ia_reg_no = ia_data.get("registration_no")
        ia_logo_key = ia_data.get("ia_logo_path")
        
        logo_path = None
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                if url_resp.get("url"):
                    logo_path = await resolve_logo_to_local_path(url_resp["url"], db)
            except: pass

        # 3. Generate PDF
        class MockObject:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    if isinstance(v, dict): setattr(self, k, MockObject(**v))
                    else: setattr(self, k, v)
        
        if "client" not in allocation_data:
            allocation_data["client"] = {"client_name": client_name, "client_code": client_code or "N/A"}
        
        if "created_at" in allocation_data and isinstance(allocation_data["created_at"], str):
            try: allocation_data["created_at"] = datetime.fromisoformat(allocation_data["created_at"].replace("Z", "+00:00"))
            except: allocation_data["created_at"] = datetime.now()

        ia_email = ia_data.get("registered_email_id") or ""
        ia = MockObject(name_of_ia=ia_name, ia_registration_number=ia_reg_no, registered_email_id=ia_email)
        allocation = MockObject(**allocation_data)
        
        pdf_buffer = AssetAllocationReportUtils.generate_pdf(allocation, ia, ia_logo_path=logo_path)
        
        # 4. Push to Bridge
        filename = f"Asset_Allocation_{client_code or allocation_id}.pdf"
        template_context = {
            "client_name": client_name,
            "ia_name": ia_name,
            "ia_reg_no": ia_reg_no or "",
            "ia_firm_name": ia_data.get("entity_name", ""),
            "ia_contact_details": f"{ia_data.get('registered_contact_number', '')} | {ia_data.get('registered_email_id', '')}"
        }

        email_payload = {
            "recipient": client_email,
            "recipient_name": client_name,
            "template_type": "ASSET_ALLOCATION_DELIVERY",
            "template_variables": json.dumps(template_context)
        }

        pdf_buffer.seek(0)
        files = {"files": (filename, pdf_buffer.read(), "application/pdf")}
        await bridge.post("/email/send", data=email_payload, files=files)

        return {"status": "success", "message": f"Asset allocation report emailed to {client_email}"}
    except Exception as e:
        logger = logging.getLogger("significia.allocation")
        logger.error(f"Email delivery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Email delivery failed: {str(e)}")
