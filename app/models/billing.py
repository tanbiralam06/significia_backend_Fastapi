import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.core.timezone import get_now_ist


# ── Plan Configuration ──────────────────────────────────────────────
# These define the pricing tiers. Used by services to enforce limits and generate invoices.
PLAN_LIMITS = {
    "free":       {"max_clients": 2,   "price_annual": 0},
    "starter":    {"max_clients": 5,   "price_annual": 100000},
    "growth":     {"max_clients": 20,  "price_annual": 300000},
    "pro":        {"max_clients": 100, "price_annual": 1000000},
    "enterprise": {"max_clients": 999999, "price_annual": 0},  # Custom pricing
}


class BillingRecord(Base):
    """
    Tracks subscription periods and invoices per tenant.
    """
    __tablename__ = "billing_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Subscription details
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Financials (in smallest currency unit, e.g., paise for INR)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")

    # Client count snapshot at billing time
    client_count_at_billing: Mapped[int] = mapped_column(Integer, default=0)

    # Invoice status
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", server_default="PENDING"
    )  # PENDING, INVOICED, PAID, OVERDUE, CANCELLED

    # Optional payment reference
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=get_now_ist, onupdate=get_now_ist)
