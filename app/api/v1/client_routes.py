"""
Client Routes — Bridge Architecture
─────────────────────────────────────
All client data operations now go through the Bridge.
No direct database connections are made from this backend.
"""
from typing import List
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_bridge_client, get_current_tenant, get_db, get_current_user
from app.services.bridge_client import BridgeClient
from app.models.tenant import Tenant
from app.schemas.client_schema import ClientCreate, ClientUpdate, ClientResponse, ClientDocumentResponse
from app.utils.reports.client_blank_form import generate_client_blank_form
from app.utils.pdf_generator import ClientPDFGenerator
from app.utils.encryption import decrypt_string

# Legacy imports removed as Bridge Architecture is fully enforced

router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES (new — no connector_id needed)
# ════════════════════════════════════════════════════════════════════

@router.post("/clients", response_model=dict)
async def create_client_bridge(
    client_in: ClientCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Create a new client via the Bridge (enforces client limit on Bridge side)."""
    try:
        data = client_in.model_dump()
        # Hash the password before sending — Bridge stores the hash
        from app.core.security import get_password_hash
        raw_password = data.pop("password")
        data["password_hash"] = get_password_hash(raw_password)
        data["email_normalized"] = data["email"].lower()

        result = await bridge.post("/clients", data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients", response_model=dict)
async def list_clients_bridge(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """List all clients via the Bridge."""
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search
    return await bridge.get("/clients", params=params)


@router.get("/clients/{client_id}", response_model=dict)
async def get_client_bridge(
    client_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a single client via the Bridge."""
    return await bridge.get(f"/clients/{client_id}")


@router.get("/clients/pan/{pan}", response_model=dict)
async def get_client_by_pan_bridge(
    pan: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get client by PAN via the Bridge."""
    result = await bridge.get("/clients", params={"search": pan})
    clients = result.get("clients", [])
    for c in clients:
        if c.get("pan_number", "").upper() == pan.upper():
            return c
    raise HTTPException(status_code=404, detail="Client not found")


@router.get("/clients/code/{code}", response_model=dict)
async def get_client_by_code_bridge(
    code: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get client by client code via the Bridge."""
    return await bridge.get(f"/clients/code/{code}")


@router.put("/clients/{client_id}", response_model=dict)
async def update_client_bridge(
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Update a client via the Bridge."""
    update_data = client_in.model_dump(exclude_unset=True)
    return await bridge.patch(f"/clients/{client_id}", update_data)


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_bridge(
    client_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Soft-delete a client via the Bridge."""
    await bridge.delete(f"/clients/{client_id}")
    return None


@router.post("/clients/{client_id}/upload-document", response_model=dict)
async def upload_client_document_bridge(
    client_id: uuid.UUID,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Upload a document for a client via the Bridge (stored in IA's own bucket)."""
    file_bytes = await file.read()
    result = await bridge.upload_file(
        f"/api/storage/upload",
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
    )
    return result


@router.get("/blank-form")
async def download_blank_registration_form(
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db)
):
    """
    Generate and download a blank registration form, pre-filled with IA details.
    """
    try:
        # 1. Fetch IA Master info from Bridge
        ia_data = await bridge.get("/ia-master")
        ia_name = decrypt_string(ia_data.get("name_of_ia")) or "____________________________"
        ia_reg_no = ia_data.get("ia_registration_number", "________________")
        
        # 2. Resolve Logo
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                signed_url = url_resp.get("url")
                if signed_url:
                    logo_path = await resolve_logo_to_local_path(signed_url, db)
            except Exception as e:
                import logging
                logging.getLogger("significia.clients").warning(f"Failed to resolve IA logo for blank form: {e}")

        # 3. Generate PDF
        pdf_buffer = generate_client_blank_form(
            ia_logo_path=logo_path,
            ia_name=ia_name,
            ia_reg_no=ia_reg_no
        )
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=Client_Registration_Form.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate blank form: {str(e)}")


@router.get("/billing/client-count", response_model=dict)
async def get_client_count_bridge(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get client count (billing metric) from the Bridge."""
    return await bridge.get("/billing/client-count")


@router.get("/report")
async def download_client_master_report(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Generate and download the Client Code Master Report for all clients via the Bridge.
    Data is enriched with assigned employee names before PDF generation.
    """
    try:
        # 1. Fetch data from Bridge in parallel
        import asyncio
        clients_task = bridge.get("/clients", params={"limit": 1000})
        employees_task = bridge.get("/employees")
        ia_task = bridge.get("/ia-master")
        
        clients_result, employees_list, ia_data = await asyncio.gather(clients_task, employees_task, ia_task)
        clients = clients_result.get("clients", [])

        if ia_data:
            ia_data["name_of_ia"] = decrypt_string(ia_data.get("name_of_ia"))
            ia_data["name_of_entity"] = decrypt_string(ia_data.get("name_of_entity"))
        
        if not clients:
            raise HTTPException(status_code=404, detail="No clients found to generate report")

        # 2. Build Employee Name Lookup Map
        # Bridge returns a list of dicts for employees.
        # We check for common name fields: full_name, name_of_employee, name
        employee_map = {}
        for emp in employees_list:
            # Handle both UUID and String IDs from Bridge response
            emp_id = str(emp.get("id") or emp.get("_id") or "")
            emp_name = emp.get("full_name") or emp.get("name_of_employee") or emp.get("name") or "Staff Member"
            if emp_id:
                employee_map[emp_id] = emp_name

        # 3. Enrich clients with employee_name for PDF generation
        for client in clients:
            assigned_id = str(client.get("assigned_employee_id") or "")
            client["employee_name"] = employee_map.get(assigned_id, "Unassigned") if assigned_id else "Unassigned"

        # 4. Generate PDF
        pdf_bytes = ClientPDFGenerator.generate_client_master_report(clients, ia_data=ia_data)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Client_Master_Report_{date_str}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate master report: {str(e)}")
@router.get("/clients/{client_id}/pdf")
async def download_client_individual_report(
    client_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Generate and download a detailed personal report for a specific client via the Bridge.
    """
    try:
        # 1. Fetch individual client data and IA profile in parallel
        import asyncio
        client_task = bridge.get(f"/clients/{client_id}")
        ia_task = bridge.get("/ia-master")
        
        client, ia_data = await asyncio.gather(client_task, ia_task)
        
        if ia_data:
            ia_data["name_of_ia"] = decrypt_string(ia_data.get("name_of_ia"))
            ia_data["name_of_entity"] = decrypt_string(ia_data.get("name_of_entity"))
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # 2. Generate PDF
        pdf_bytes = ClientPDFGenerator.generate_client_report(client, ia_data=ia_data)
        
        client_name = client.get("client_name", "Client").replace(" ", "_")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Report_{client_name}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate client report: {str(e)}")
