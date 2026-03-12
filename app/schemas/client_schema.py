from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr
import uuid
from datetime import datetime, date

class ClientLoginRequest(BaseModel):
    email: EmailStr
    password: str

class ClientTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ClientBase(BaseModel):
    email: EmailStr
    client_name: str
    date_of_birth: date
    pan_number: str
    phone_number: str
    address: str
    occupation: str
    gender: str
    marital_status: str
    nationality: str
    residential_status: str
    tax_residency: str
    pep_status: str
    father_name: str
    mother_name: str
    spouse_name: Optional[str] = None
    
    annual_income: float
    net_worth: float
    income_source: str
    fatca_compliance: str
    existing_portfolio_value: Optional[float] = 0.0
    existing_portfolio_composition: Optional[str] = None
    
    bank_account_number: str
    bank_name: str
    bank_branch: str
    ifsc_code: str
    demat_account_number: Optional[str] = None
    trading_account_number: Optional[str] = None
    
    risk_profile: str
    investment_experience: str
    investment_objectives: str
    investment_horizon: str
    liquidity_needs: str
    
    advisor_name: str
    nominee_name: Optional[str] = None
    nominee_relationship: Optional[str] = None
    declaration_signed: bool = False
    declaration_date: Optional[date] = None
    assigned_employee_id: Optional[uuid.UUID] = None

class ClientCreate(ClientBase):
    password: str
    client_code: str
    client_signature_path: Optional[str] = None
    advisor_signature_path: Optional[str] = None

class ClientUpdate(BaseModel):
    phone_number: Optional[str] = None
    address: Optional[str] = None
    annual_income: Optional[float] = None
    net_worth: Optional[float] = None
    assigned_employee_id: Optional[uuid.UUID] = None

class ClientResponse(ClientBase):
    id: uuid.UUID
    client_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    assigned_employee_id: Optional[uuid.UUID] = None
    
    client_signature_path: Optional[str] = None
    advisor_signature_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
