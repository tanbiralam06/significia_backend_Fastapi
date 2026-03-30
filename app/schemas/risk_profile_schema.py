from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from uuid import UUID
from datetime import datetime

class Q2Factors(BaseModel):
    a: str = Field(..., description="Short-term appreciation (A/B/C)")
    b: str = Field(..., description="Long-term appreciation (A/B/C)")
    c: str = Field(..., description="Takeover potential (A/B/C)")
    d: str = Field(..., description="6-month price trend (A/B/C)")
    e: str = Field(..., description="5-year price trend (A/B/C)")
    f: str = Field(..., description="Peer recommendation (A/B/C)")
    g: str = Field(..., description="Price drop risk (A/B/C)")
    h: str = Field(..., description="Dividend potential (A/B/C)")

class RiskAssessmentAnswers(BaseModel):
    q1: str
    q2: Q2Factors
    q3: str
    q4: str
    q5: str
    q6: str
    q7: str
    q8: str
    q9: str
    q10: str
    q11: str
    q12: str
    q13: str
    q14: str
    q15: str
    q16: str

class RiskAssessmentCreate(BaseModel):
    client_code: str = Field(..., pattern="^[A-Z]{1,10}[0-9]{1,10}$")
    answers: RiskAssessmentAnswers
    include_ai: bool = False
    disclaimer_text: Optional[str] = None
    discussion_notes: Optional[str] = ""
    form_name: Optional[str] = "Sample"

class RiskAssessmentCalculateRequest(BaseModel):
    answers: RiskAssessmentAnswers

class QuestionScoreDetail(BaseModel):
    score: int
    max: int
    details: Optional[Dict[str, Dict[str, object]]] = None

class RiskAssessmentCalculateResponse(BaseModel):
    success: bool
    total_score: int
    question_scores: Dict[str, QuestionScoreDetail]
    risk_tier: str
    recommendation: str

class RiskAssessmentResponse(BaseModel):
    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    client_code: Optional[str] = None
    calculated_score: int
    assigned_risk_tier: str
    tier_recommendation: Optional[str] = None
    form_name: str
    assessment_timestamp: datetime

    class Config:
        from_attributes = True

class SaveAssessmentResponse(BaseModel):
    success: bool
    assessment_id: UUID
    risk_id: UUID
    total_score: int
    risk_tier: str
    client_code: str
    ia_registration_number: str
