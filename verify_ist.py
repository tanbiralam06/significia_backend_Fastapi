import sys
import os

# Add the current directory to sys.path to import app
sys.path.append(os.getcwd())

from datetime import datetime, timezone, timedelta
from app.core.timezone import get_now_ist, to_ist, IST

def test_timezone_logic():
    print(f"Current System Time: {datetime.now()}")
    
    now_ist = get_now_ist()
    print(f"Current IST (Aware): {now_ist}")
    print(f"Current IST (Naive): {now_ist.replace(tzinfo=None)}")
    
    # Check offset
    expected_offset = timedelta(hours=5, minutes=30)
    actual_offset = now_ist.utcoffset()
    
    if actual_offset == expected_offset:
        print("✅ IST Offset is correct (+5:30)")
    else:
        print(f"❌ IST Offset is INCORRECT: {actual_offset}")

    # Test conversion from UTC
    utc_now = datetime.now(timezone.utc)
    converted_ist = to_ist(utc_now)
    print(f"UTC Now: {utc_now} -> Converted IST: {converted_ist}")
    
    if (converted_ist - utc_now).total_seconds() == 0:
        print("✅ UTC to IST conversion preserved the exact moment in time.")
    else:
        print("❌ UTC to IST conversion FAILED.")

    # Test naive conversion
    naive_utc_ish = datetime.utcnow()
    converted_from_naive = to_ist(naive_utc_ish)
    print(f"Naive 'UTC' Now: {naive_utc_ish} -> Converted IST: {converted_from_naive}")

if __name__ == "__main__":
    test_timezone_logic()
