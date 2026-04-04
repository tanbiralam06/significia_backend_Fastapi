import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import SiloBase
from app.core.timezone import get_now_ist


class RiskAssessment(SiloBase):
    """
    Stores risk assessment questionnaire responses and results for a client.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Question Responses
    q1_interest_choice: Mapped[str] = mapped_column(String(10), nullable=False)
    q2_importance_factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    q3_probability_bet: Mapped[str] = mapped_column(String(10), nullable=False)
    q4_portfolio_choice: Mapped[str] = mapped_column(String(10), nullable=False)
    q5_loss_behavior: Mapped[str] = mapped_column(String(10), nullable=False)
    q6_market_reaction: Mapped[str] = mapped_column(String(10), nullable=False)
    q7_fund_selection: Mapped[str] = mapped_column(String(10), nullable=False)
    q8_experience_level: Mapped[str] = mapped_column(String(10), nullable=False)
    q9_time_horizon: Mapped[str] = mapped_column(String(10), nullable=False)
    q10_net_worth: Mapped[str] = mapped_column(String(10), nullable=False)
    q11_age_range: Mapped[str] = mapped_column(String(10), nullable=False)
    q12_income_range: Mapped[str] = mapped_column(String(10), nullable=False)
    q13_expense_range: Mapped[str] = mapped_column(String(10), nullable=False)
    q14_dependents: Mapped[str] = mapped_column(String(10), nullable=False)
    q15_active_loan: Mapped[str] = mapped_column(String(10), nullable=False)
    q16_investment_objective: Mapped[str] = mapped_column(String(10), nullable=False)

    # Calculation Results
    calculated_score: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_risk_tier: Mapped[str] = mapped_column(String(100), nullable=False)
    tier_recommendation: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata and Notes
    disclaimer_text: Mapped[Optional[str]] = mapped_column(Text)
    discussion_notes: Mapped[Optional[str]] = mapped_column(Text)
    question_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Form Identification
    form_name: Mapped[str] = mapped_column(String(255), default="Sample", server_default="Sample")

    # Timestamps
    assessment_timestamp: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)

    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile", foreign_keys=[client_id])


class ClientRiskMaster(SiloBase):
    """
    Links a client to their current risk category and IA registration.
    """
    __tablename__ = "client_risk_master"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ia_registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    portfolio_name: Mapped[str] = mapped_column(String(100), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)

    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile", foreign_keys=[client_id])


class RiskQuestionnaire(SiloBase):
    """
    Stores custom questionnaire definitions (questions, options, weights).
    """
    __tablename__ = "risk_questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft") # draft, active, archived
    
    questions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    categories: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    max_possible_score: Mapped[float] = mapped_column(Integer, default=0)
    disclaimer: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)


class CustomRiskAssessment(SiloBase):
    """
    Stores responses to custom questionnaires.
    """
    __tablename__ = "custom_risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_questionnaires.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    responses: Mapped[dict] = mapped_column(JSONB, nullable=False) # { "q_0": { "option_index": 0, "score": 5 } }
    total_score: Mapped[float] = mapped_column(Integer, nullable=False)
    category_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    discussion_notes: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    questionnaire: Mapped["RiskQuestionnaire"] = relationship("RiskQuestionnaire")
    client: Mapped["ClientProfile"] = relationship("ClientProfile", foreign_keys=[client_id])
