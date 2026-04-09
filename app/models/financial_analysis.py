import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Float, ForeignKey, Text, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import SiloBase
from app.core.timezone import get_now_ist


class FinancialAnalysisProfile(SiloBase):
    """
    Captures a snapshot of client financial data at the time of analysis.
    Each analysis run creates a new profile record.
    """
    __tablename__ = "financial_analysis_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Personal Info Snapshot
    pan: Mapped[Optional[str]] = mapped_column(String(20))
    contact: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    annual_income: Mapped[float] = mapped_column(Float, nullable=False)

    # Spouse Info
    spouse_name: Mapped[Optional[str]] = mapped_column(String(255))
    spouse_dob: Mapped[Optional[date]] = mapped_column(Date)
    spouse_occupation: Mapped[Optional[str]] = mapped_column(String(100))

    # Children (JSON array of {name, dob, occupation})
    children: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    # Financial Data (JSONB)
    expenses: Mapped[dict] = mapped_column(JSONB, nullable=False)       # 11 expense categories
    assets: Mapped[dict] = mapped_column(JSONB, nullable=False)         # 4 asset categories
    liabilities: Mapped[dict] = mapped_column(JSONB, nullable=False)    # 3 liability types
    insurance: Mapped[dict] = mapped_column(JSONB, nullable=False)      # 8 insurance fields

    # Assumptions (JSONB with 14 parameters)
    assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Medical Bonus
    medical_bonus_years: Mapped[float] = mapped_column(Float, default=0.0)
    medical_bonus_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # Investment Allocation
    education_investment_pct: Mapped[float] = mapped_column(Float, default=0.0)
    marriage_investment_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # AI & Report Options
    exclude_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    disclaimer_text: Mapped[Optional[str]] = mapped_column(Text)
    discussion_notes: Mapped[Optional[str]] = mapped_column(Text)
    record_version_control_statement: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)

    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile", foreign_keys=[client_id])
    results: Mapped[list["FinancialAnalysisResult"]] = relationship(
        "FinancialAnalysisResult", back_populates="profile", cascade="all, delete-orphan"
    )


class FinancialAnalysisResult(SiloBase):
    """
    Stores the output of financial calculations and AI commentary.
    One result per profile (1:1 in practice, but modeled as 1:N for flexibility).
    """
    __tablename__ = "financial_analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("financial_analysis_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Calculation Results (JSONB)
    calculations: Mapped[dict] = mapped_column(JSONB, nullable=False)       # Comprehensive results
    hlv_data: Mapped[dict] = mapped_column(JSONB, nullable=False)           # HLV-specific
    medical_data: Mapped[dict] = mapped_column(JSONB, nullable=False)       # Medical-specific
    cash_flow_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)       # Year-by-year projection
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)              # All AI commentary sections

    # Summary Score
    financial_health_score: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    profile: Mapped["FinancialAnalysisProfile"] = relationship(
        "FinancialAnalysisProfile", back_populates="results"
    )
    client: Mapped["ClientProfile"] = relationship("ClientProfile", foreign_keys=[client_id])
