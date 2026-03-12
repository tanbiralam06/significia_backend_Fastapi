import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.schemas.client_schema import ClientCreate
from app.services.client_service import ClientService
from app.models.client import ClientProfile

def test_registration():
    db = SessionLocal()
    try:
        # 1. Test Age Validation (Under 18)
        print("Testing Age Validation (Under 18)...")
        under_18_dob = date.today() - timedelta(days=365 * 17)
        try:
            ClientCreate(
                email="under18@example.com",
                client_name="Under 18",
                date_of_birth=under_18_dob,
                pan_number="ABCDE1111A",
                phone_number="1234567890",
                address="Test Address",
                occupation="Student",
                gender="Male",
                marital_status="Single",
                nationality="Indian",
                residential_status="Resident",
                tax_residency="India",
                pep_status="None",
                father_name="Father",
                mother_name="Mother",
                annual_income=100000,
                net_worth=500000,
                income_source="Salary",
                fatca_compliance="Yes",
                bank_account_number="12345",
                bank_name="Bank",
                bank_branch="Branch",
                ifsc_code="IFSC001",
                risk_profile="Low",
                investment_experience="Beginner",
                investment_objectives="Growth",
                investment_horizon="Short",
                liquidity_needs="High",
                advisor_name="Advisor",
                advisor_registration_number="REG001",
                password="password123"
            )
            print("FAILED: Age validation did not catch under 18")
        except ValueError as e:
            print(f"SUCCESS: Caught age validation error: {e}")

        # 2. Test Client Code Generation
        print("\nTesting Client Code Generation...")
        over_18_dob = date.today() - timedelta(days=365 * 25)
        
        # Determine next code
        next_code = ClientService.generate_next_client_code(db)
        print(f"Generated Code: {next_code}")
        
        if not next_code.startswith("C") or len(next_code) != 11:
             print(f"FAILED: format incorrect. Expected C + 10 digits, got {next_code}")
        else:
             print(f"SUCCESS: format correct: {next_code}")

    except Exception as e:
        print(f"Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_registration()
