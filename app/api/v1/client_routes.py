from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database.remote_session import get_remote_session
from app.schemas.client_schema import ClientCreate, ClientUpdate, ClientResponse
from app.services.client_service import ClientService

router = APIRouter()

# Note: All routes require a 'connector_id' to know which remote DB to use
# The 'get_remote_session' dependency handles connection, decryption, and schema context.

@router.post("/{connector_id}/clients", response_model=ClientResponse)
def create_client(
    connector_id: uuid.UUID,
    client_in: ClientCreate,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        return ClientService.create_client(remote_db, client_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{connector_id}/clients", response_model=List[ClientResponse])
def list_clients(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    return ClientService.list_clients(remote_db)

@router.get("/{connector_id}/clients/{client_id}", response_model=ClientResponse)
def get_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.get_client(remote_db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{connector_id}/clients/{client_id}", response_model=ClientResponse)
def update_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    remote_db: Session = Depends(get_remote_session)
):
    client = ClientService.update_client(remote_db, client_id, client_in)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
