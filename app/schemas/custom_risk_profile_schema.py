from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

class RiskOption(BaseModel):
    id: str
    text: str
    score: float

class RiskQuestion(BaseModel):
    id: str
    text: str
    options: List[RiskOption]

class RiskCategory(BaseModel):
    name: str
    min_score: float
    max_score: float
    color: Optional[str] = "#000000"
    description: Optional[str] = ""

class RiskQuestionnaireBase(BaseModel):
    portfolio_name: str
    questions: List[RiskQuestion]
    categories: List[RiskCategory]
    status: str = "draft"
    max_possible_score: float = 0.0
    disclaimer: Optional[str] = None

class RiskQuestionnaireCreate(RiskQuestionnaireBase):
    pass

class RiskQuestionnaireUpdate(BaseModel):
    portfolio_name: Optional[str] = None
    questions: Optional[List[RiskQuestion]] = None
    categories: Optional[List[RiskCategory]] = None
    status: Optional[str] = None
    max_possible_score: Optional[float] = None
    disclaimer: Optional[str] = None

class RiskQuestionnaireResponse(RiskQuestionnaireBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CustomRiskAssessmentCreate(BaseModel):
    questionnaire_id: UUID
    client_code: str
    responses: Dict[str, Any] # question_id -> { "option_id": str, "score": float }
    discussion_notes: Optional[str] = None

class CustomRiskAssessmentResponse(BaseModel):
    id: UUID
    questionnaire_id: UUID
    client_id: UUID
    responses: Dict[str, Any]
    total_score: float
    category_name: Optional[str]
    discussion_notes: Optional[str]
    submitted_at: datetime
    
    # Optional fields for UI
    portfolio_name: Optional[str] = None
    client_name: Optional[str] = None
    client_code: Optional[str] = None

    class Config:
        from_attributes = True
