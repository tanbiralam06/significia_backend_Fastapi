from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator
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
    aadhar_number: Optional[str] = None
    passport_number: Optional[str] = None
    
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
    advisor_registration_number: str
    client_date: Optional[date] = None
    nominee_name: Optional[str] = None
    nominee_relationship: Optional[str] = None
    previous_advisor_name: Optional[str] = None
    referral_source: Optional[str] = None
    declaration_signed: bool = False
    declaration_date: Optional[date] = None
    assigned_employee_id: Optional[uuid.UUID] = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Age must be at least 18 years")
        return v

    @model_validator(mode='after')
    def validate_identification(self) -> 'ClientBase':
        if self.residential_status == "Resident Individual":
            if not self.aadhar_number:
                raise ValueError("Aadhar number is required for Resident Individual")
            if not self.aadhar_number.isdigit() or len(self.aadhar_number) != 12:
                raise ValueError("Aadhar number must be exactly 12 digits")
        else:
            if not self.passport_number:
                raise ValueError("Passport number is required for non-resident status")
        return self

class ClientCreate(ClientBase):
    password: str
    client_signature_path: Optional[str] = None
    advisor_signature_path: Optional[str] = None

class ClientUpdate(BaseModel):
    # Personal info
    email: Optional[EmailStr] = None
    client_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    pan_number: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    residential_status: Optional[str] = None
    tax_residency: Optional[str] = None
    pep_status: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    spouse_name: Optional[str] = None
    aadhar_number: Optional[str] = None
    passport_number: Optional[str] = None
    
    # Financial info
    annual_income: Optional[float] = None
    net_worth: Optional[float] = None
    income_source: Optional[str] = None
    fatca_compliance: Optional[str] = None
    existing_portfolio_value: Optional[float] = None
    existing_portfolio_composition: Optional[str] = None
    
    # Banking info
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    ifsc_code: Optional[str] = None
    demat_account_number: Optional[str] = None
    trading_account_number: Optional[str] = None
    
    # Investment info
    risk_profile: Optional[str] = None
    investment_experience: Optional[str] = None
    investment_objectives: Optional[str] = None
    investment_horizon: Optional[str] = None
    liquidity_needs: Optional[str] = None
    
    # Metadata & Nominee
    advisor_name: Optional[str] = None
    advisor_registration_number: Optional[str] = None
    client_date: Optional[date] = None
    nominee_name: Optional[str] = None
    nominee_relationship: Optional[str] = None
    previous_advisor_name: Optional[str] = None
    referral_source: Optional[str] = None
    declaration_signed: Optional[bool] = None
    declaration_date: Optional[date] = None
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
    aadhar_number: Optional[str] = None
    passport_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
