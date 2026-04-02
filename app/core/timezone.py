from datetime import datetime, timedelta, timezone

# ── IST Utility (UTC+5:30) ──────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

def get_now_ist() -> datetime:
    """Returns the current aware datetime in IST."""
    return datetime.now(IST)

def to_ist(dt: datetime) -> datetime:
    """Converts any datetime to IST."""
    if dt.tzinfo is None:
        # Assume UTC if no tzinfo provided
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)
