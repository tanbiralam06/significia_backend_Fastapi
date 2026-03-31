import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class TokenUsage(Base):
    """
    Privacy-preserving billing meter.
    Stores only WHAT was used and HOW MANY times — never WHO or WHAT DATA.

    Example records:
        tenant_id=Bunty, metric="client_count",    value=5,  recorded_at=2026-04-01
        tenant_id=Bunty, metric="risk_reports",     value=12, recorded_at=2026-04-01
        tenant_id=Bunty, metric="pdf_generated",    value=8,  recorded_at=2026-04-01
    """
    __tablename__ = "token_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # The type of usage being tracked (e.g., "client_count", "risk_reports", "pdf_generated")
    metric: Mapped[str] = mapped_column(String(100), nullable=False)

    # The count / value (just a number — no personal data)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # When this measurement was recorded
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
