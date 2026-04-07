"""
Pydantic schemas for Financial Analysis module.
Handles request validation and response serialization.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Input Sub-schemas ───

class ChildInfo(BaseModel):
    name: str
    dob: Optional[date] = None
    occupation: Optional[str] = None


class ExpensesInput(BaseModel):
    """11 expense categories from finplan.py (exact match)."""
    hh: Optional[float] = 0.0          # Household
    med: Optional[float] = 0.0         # Medical
    travel: Optional[float] = 0.0      # Travel
    elec: Optional[float] = 0.0        # Electricity
    tele: Optional[float] = 0.0        # Telephone
    maid: Optional[float] = 0.0        # Maid
    edu: Optional[float] = 0.0         # Education
    ent: Optional[float] = 0.0         # Entertainment
    emi: Optional[float] = 0.0         # EMI
    savings: Optional[float] = 0.0     # Savings/Investment
    misc: Optional[float] = 0.0        # Miscellaneous

    @property
    def total(self) -> float:
        return sum([
            self.hh, self.med, self.travel, self.elec, self.tele,
            self.maid, self.edu, self.ent, self.emi, self.savings, self.misc
        ])


class AssetsInput(BaseModel):
    """4 asset categories from finplan.py."""
    land: Optional[float] = 0.0        # Land & Building
    inv: Optional[float] = 0.0         # Investments
    cash: Optional[float] = 0.0        # Cash & Bank
    retirement: Optional[float] = 0.0  # Retirement savings

    @property
    def total(self) -> float:
        return sum([self.land, self.inv, self.cash, self.retirement])


class OtherLiability(BaseModel):
    label: str
    amount: Optional[float] = 0.0


class LiabilitiesInput(BaseModel):
    """3 liability types from finplan.py + dynamic others."""
    personal: Optional[float] = 0.0
    cc: Optional[float] = 0.0          # Credit Card
    hb: Optional[float] = 0.0          # Home/Building
    others: List[OtherLiability] = []

    @property
    def total(self) -> float:
        others_total = sum([o.amount for o in self.others])
        return self.personal + self.cc + self.hb + others_total


class InsuranceInput(BaseModel):
    """8 insurance fields from finplan.py."""
    life_cover: Optional[float] = 0.0
    life_premium: Optional[float] = 0.0
    med_cover: Optional[float] = 0.0
    med_premium: Optional[float] = 0.0
    veh_cover: Optional[float] = 0.0
    veh_premium: Optional[float] = 0.0
    other_cover: Optional[float] = 0.0
    other_premium: Optional[float] = 0.0


class AssumptionsInput(BaseModel):
    """14 calculation assumption parameters with sensible defaults."""
    retirement_age: int = 0
    le_client: int = 0         # Life expectancy - client
    le_spouse: int = 0         # Life expectancy - spouse
    inflation: float = 0
    medical_inflation: float = 0
    pre_ret_rate: float = 0  # Pre-retirement return rate
    post_ret_rate: float = 0  # Post-retirement return rate
    sol_hlv: float = 0       # Standard of living % for HLV
    sol_ret: float = 0       # Standard of living % for retirement
    inc_inc_rate: float = 0   # Income increment rate
    child_education_corpus: float = 0
    education_years: int = 0
    child_marriage_corpus: float = 0
    marriage_years: int = 0

    @field_validator('retirement_age')
    @classmethod
    def validate_retirement_age(cls, v):
        if v < 40 or v > 80:
            raise ValueError('Retirement age must be between 40 and 80')
        return v


# ─── Main Request Schema ───

class FinancialAnalysisCreate(BaseModel):
    """Main request body for creating a financial analysis."""
    client_id: uuid.UUID

    # Personal info snapshot
    pan: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    occupation: str
    dob: date
    annual_income: float = Field(gt=0)

    # Spouse
    spouse_name: Optional[str] = None
    spouse_dob: Optional[date] = None
    spouse_occupation: Optional[str] = None

    # Children
    children: List[ChildInfo] = []

    # Financial data
    expenses: ExpensesInput
    assets: AssetsInput
    liabilities: LiabilitiesInput
    insurance: InsuranceInput

    # Assumptions
    assumptions: AssumptionsInput = AssumptionsInput()

    # Medical bonus
    medical_bonus_years: float = 0
    medical_bonus_percentage: float = 0

    # Investment allocation
    education_investment_pct: float = 0
    marriage_investment_pct: float = 0

    # Report options
    exclude_ai: bool = False
    disclaimer_text: Optional[str] = None
    discussion_notes: Optional[str] = None


# ─── Response Schemas ───

class FinancialAnalysisSummary(BaseModel):
    """List view — minimal info per analysis."""
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: Optional[str] = None
    calculations: Optional[dict] = None
    hlv_data: Optional[dict] = None
    financial_health_score: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialAnalysisResponse(BaseModel):
    """Full analysis result response."""
    id: uuid.UUID
    profile_id: uuid.UUID
    client_id: uuid.UUID

    # Core results
    calculations: dict
    hlv_data: dict
    medical_data: dict
    cash_flow_analysis: Optional[List[dict]] = None
    ai_analysis: Optional[dict] = None
    financial_health_score: int

    # Profile snapshot
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    dob: Optional[date] = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalculationDetailsResponse(BaseModel):
    """Step-by-step breakdown of calculations."""
    result_id: uuid.UUID
    client_id: uuid.UUID
    sections: list  # Array of {section, steps[]}
    created_at: datetime
