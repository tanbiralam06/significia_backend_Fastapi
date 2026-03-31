from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class AssetAllocationBase(BaseModel):
    equities_percentage: float = 0.0
    debt_securities_percentage: float = 0.0
    commodities_percentage: float = 0.0
    
    stocks_percentage: float = 0.0
    mutual_fund_equity_percentage: float = 0.0
    ulip_equity_percentage: float = 0.0
    
    fixed_deposits_bonds_percentage: float = 0.0
    mutual_fund_debt_percentage: float = 0.0
    ulip_debt_percentage: float = 0.0
    
    gold_etf_percentage: float = 0.0
    silver_etf_percentage: float = 0.0
    
    generate_system_conclusion: bool = True
    system_conclusion: Optional[str] = None
    discussion_notes: Optional[str] = None
    disclaimer_text: Optional[str] = None

class AssetAllocationCreate(AssetAllocationBase):
    client_code: str
    ia_registration_number: str
    assigned_risk_tier: str
    tier_recommendation: str

class AssetAllocationResponse(AssetAllocationBase):
    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    client_code: Optional[str] = None
    assigned_risk_tier: Optional[str] = None
    tier_recommendation: Optional[str] = None
    system_conclusion: Optional[str] = None
    total_allocation: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClientValidateResponse(BaseModel):
    success: bool
    client_name: str
    registration_number: str
    category_name: str
    error: Optional[str] = None

class AssetAllocationSaveResponse(BaseModel):
    success: bool
    allocation_id: UUID
    message: str
