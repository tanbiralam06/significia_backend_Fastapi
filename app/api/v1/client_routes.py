from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database.remote_session import get_remote_session
from app.schemas.client_schema import ClientCreate, ClientUpdate, ClientResponse
from app.services.client_service import ClientService
from app.utils.reports.client_blank_form import generate_client_blank_form
from app.utils.file_utils import resolve_logo_to_local_path
from app.models.ia_master import IAMaster

router = APIRouter()

# Note: All routes require a 'connector_id' to know which remote DB to use
# The 'get_remote_session' dependency handles connection, decryption, and schema context.

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
        # Get IA Logo if available
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

from fastapi import UploadFile, File, Form
from app.schemas.client_schema import ClientDocumentResponse

@router.post("/{connector_id}/clients/{client_id}/upload-document", response_model=ClientDocumentResponse)
async def upload_client_document(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    remote_db: Session = Depends(get_remote_session)
):
    """
    Upload a document for a specific client. 
    The file will correctly route directly to 'Clients/{Client Name}' bucket folder.
    """
    try:
        doc = await ClientService.upload_document(remote_db, client_id, document_type, file)
        from app.services.storage_service import StorageService
        driver = StorageService.get_tenant_storage(remote_db)
        if driver and not doc.file_path.startswith(('http://', 'https://')):
            doc.file_path = await driver.get_file_url(doc.file_path)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

