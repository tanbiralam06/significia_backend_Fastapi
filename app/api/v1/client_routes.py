"""
Client Routes — Bridge Architecture
─────────────────────────────────────
All client data operations now go through the Bridge.
No direct database connections are made from this backend.
"""
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_bridge_client, get_current_tenant, get_db, get_current_user
from app.services.bridge_client import BridgeClient
from app.models.tenant import Tenant
from app.schemas.client_schema import ClientCreate, ClientUpdate, ClientResponse, ClientDocumentResponse
from app.utils.reports.client_blank_form import generate_client_blank_form
from app.utils.pdf_generator import ClientPDFGenerator

# Legacy imports kept for backward compatibility during transition
from app.database.remote_session import get_remote_session

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

        result = await bridge.post("/api/clients", data)
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
    return await bridge.get("/api/clients", params=params)


@router.get("/clients/{client_id}", response_model=dict)
async def get_client_bridge(
    client_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a single client via the Bridge."""
    return await bridge.get(f"/api/clients/{client_id}")


@router.get("/clients/pan/{pan}", response_model=dict)
async def get_client_by_pan_bridge(
    pan: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get client by PAN via the Bridge."""
    result = await bridge.get("/api/clients", params={"search": pan})
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
    result = await bridge.get("/api/clients", params={"search": code})
    clients = result.get("clients", [])
    for c in clients:
        if c.get("client_code", "").upper() == code.upper():
            return c
    raise HTTPException(status_code=404, detail="Client not found")


@router.put("/clients/{client_id}", response_model=dict)
async def update_client_bridge(
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Update a client via the Bridge."""
    update_data = client_in.model_dump(exclude_unset=True)
    return await bridge.patch(f"/api/clients/{client_id}", update_data)


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_bridge(
    client_id: uuid.UUID,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Soft-delete a client via the Bridge."""
    await bridge.delete(f"/api/clients/{client_id}")
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


@router.get("/billing/client-count", response_model=dict)
async def get_client_count_bridge(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get client count (billing metric) from the Bridge."""
    return await bridge.get("/api/billing/client-count")


# ════════════════════════════════════════════════════════════════════
#  LEGACY ROUTES (kept for backward compatibility during transition)
#  These still use connector_id + get_remote_session
# ════════════════════════════════════════════════════════════════════

from app.services.client_service import ClientService
from app.models.ia_master import IAMaster
from app.utils.file_utils import resolve_logo_to_local_path

@router.post("/{connector_id}/clients", response_model=ClientResponse)
async def create_client(
    connector_id: uuid.UUID,
    client_in: ClientCreate,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        client = ClientService.create_client(remote_db, client_in)
        return await ClientService.sign_client_urls(client, remote_db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connector_id}/clients", response_model=List[ClientResponse])
async def list_clients(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    clients = ClientService.list_clients(remote_db)
    for client in clients:
        await ClientService.sign_client_urls(client, remote_db)
    return clients

@router.get("/{connector_id}/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.get_client(remote_db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await ClientService.sign_client_urls(client, remote_db)

@router.get("/{connector_id}/clients/pan/{pan}", response_model=ClientResponse)
async def get_client_by_pan(
    connector_id: uuid.UUID,
    pan: str,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.get_client_by_pan(remote_db, pan)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await ClientService.sign_client_urls(client, remote_db)

@router.get("/{connector_id}/clients/code/{code}", response_model=ClientResponse)
async def get_client_by_code(
    connector_id: uuid.UUID,
    code: str,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.get_client_by_code(remote_db, code)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await ClientService.sign_client_urls(client, remote_db)

@router.put("/{connector_id}/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.update_client(remote_db, client_id, client_in)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await ClientService.sign_client_urls(client, remote_db)

@router.delete("/{connector_id}/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    success = ClientService.delete_client(remote_db, client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return None

@router.get("/{connector_id}/clients/{client_id}/pdf")
def download_client_report(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        pdf_bytes, filename = ClientService.generate_pdf(remote_db, client_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{connector_id}/report")
def download_master_report(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        pdf_bytes, filename = ClientService.generate_master_report(remote_db)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{connector_id}/blank-form")
async def download_client_blank_form(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Download a blank client registration form as PDF."""
    try:
        ia_logo_path = None
        ia_master = remote_db.query(IAMaster).first()
        if ia_master:
            ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)

        pdf_stream = generate_client_blank_form(ia_logo_path=ia_logo_path)
        
        filename = "Client_Registration_Form.pdf"
        return Response(
            content=pdf_stream.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{connector_id}/clients/{client_id}/upload-document", response_model=ClientDocumentResponse)
async def upload_client_document(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    remote_db: Session = Depends(get_remote_session)
):
    try:
        doc = await ClientService.upload_document(remote_db, client_id, document_type, file)
        from app.services.storage_service import StorageService
        driver = StorageService.get_tenant_storage(remote_db)
        if driver and not doc.file_path.startswith(('http://', 'https://')):
            doc.file_path = await driver.get_file_url(doc.file_path)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
