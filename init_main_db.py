from app.database.session import engine
from sqlalchemy import text
from app.database.base import Base
# Import ONLY global models for Master DB
from app.models.user import User
from app.models.tenant import Tenant
from app.models.connector import Connector
from app.models.api_key import ApiKey
from app.models.refresh_token import RefreshToken
from app.models.user_session import UserSession
from app.models.login_attempt import LoginAttempt
from app.models.mfa_secret import MFASecret
from app.models.password_reset_token import PasswordResetToken
from app.models.verification_token import VerificationToken

def init():
    print("Initializing main database (Master Orchestrator)...")
    # Only the imported models above will be created in the bind engine (Master DB)
    Base.metadata.create_all(bind=engine)
    print("Master tables created successfully.")
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        print(f"Current tables in public schema: {tables}")

if __name__ == "__main__":
    init()
