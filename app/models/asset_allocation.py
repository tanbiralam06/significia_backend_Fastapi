import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import SiloBase

class AssetAllocation(SiloBase):
    __tablename__ = "asset_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ia_registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    assigned_risk_tier: Mapped[str] = mapped_column(String(100), nullable=False)
    tier_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Main Asset Percentages
    equities_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    debt_securities_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    commodities_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Equity Sub-Assets
    stocks_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    mutual_fund_equity_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    ulip_equity_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Debt Sub-Assets
    fixed_deposits_bonds_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    mutual_fund_debt_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    ulip_debt_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Commodities Sub-Assets
    gold_etf_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    silver_etf_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Content and Documentation
    system_conclusion: Mapped[Optional[str]] = mapped_column(Text)
    generate_system_conclusion: Mapped[bool] = mapped_column(Boolean, default=True)
    discussion_notes: Mapped[Optional[str]] = mapped_column(Text)
    disclaimer_text: Mapped[Optional[str]] = mapped_column(Text)
    
    total_allocation: Mapped[float] = mapped_column(Float, default=100.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client: Mapped["ClientProfile"] = relationship("ClientProfile")
