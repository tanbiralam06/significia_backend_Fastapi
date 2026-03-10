from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.schemas.connector_schema import ConnectorCreate, ConnectorUpdate, ConnectorResponse
from app.services.connector_service import ConnectorService
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=ConnectorResponse)
def create_connector(
    connector_in: ConnectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ConnectorService.create_connector(db, current_user.tenant_id, connector_in)

@router.get("/", response_model=List[ConnectorResponse])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ConnectorService.list_connectors(db, current_user.tenant_id)

@router.get("/{connector_id}", response_model=ConnectorResponse)
def get_connector(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    connector = ConnectorService.get_connector(db, connector_id, current_user.tenant_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector

@router.put("/{connector_id}", response_model=ConnectorResponse)
def update_connector(
    connector_id: uuid.UUID,
    connector_in: ConnectorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    connector = ConnectorService.update_connector(db, connector_id, current_user.tenant_id, connector_in)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector

@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = ConnectorService.delete_connector(db, connector_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connector not found")
    return None

@router.post("/{connector_id}/test")
def test_connection(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = ConnectorService.test_connection(db, connector_id, current_user.tenant_id)
    if not success:
        return {"status": "error", "message": "Connection failed. Please check credentials and host accessibility."}
    return {"status": "success", "message": "Connection established successfully."}

@router.post("/{connector_id}/initialize")
def initialize_database(
    connector_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.provisioner_service import ProvisionerService
    success = ProvisionerService.initialize_database(db, connector_id, current_user.tenant_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Database initialization failed. Ensure the connection is valid and the user has permission to create tables."
        )
    return {"status": "success", "message": "Database initialized with core tables."}
