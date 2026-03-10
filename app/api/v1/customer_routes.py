from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.remote_session import get_remote_session
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate, CustomerResponse
from app.services.customer_service import CustomerService

router = APIRouter()

# Note: All routes require a 'connector_id' to know which remote DB to use
# The 'get_remote_session' dependency handles connection, decryption, and schema context.

@router.post("/{connector_id}/customers", response_model=CustomerResponse)
def create_customer(
    connector_id: uuid.UUID,
    customer_in: CustomerCreate,
    remote_db: Session = Depends(get_remote_session)
):
    return CustomerService.create_customer(remote_db, customer_in)

@router.get("/{connector_id}/customers", response_model=List[CustomerResponse])
def list_customers(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    return CustomerService.list_customers(remote_db)

@router.get("/{connector_id}/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    connector_id: uuid.UUID,
    customer_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    customer = CustomerService.get_customer(remote_db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.put("/{connector_id}/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    connector_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_in: CustomerUpdate,
    remote_db: Session = Depends(get_remote_session)
):
    customer = CustomerService.update_customer(remote_db, customer_id, customer_in)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.delete("/{connector_id}/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    connector_id: uuid.UUID,
    customer_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    success = CustomerService.delete_customer(remote_db, customer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None
