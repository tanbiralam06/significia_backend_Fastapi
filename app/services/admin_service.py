from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.schemas.admin_schema import ClientProvisionRequest
from app.repositories.user_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.ia_master_repository import IAMasterRepository
from app.models.user import User

class AdminService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.tenant_repo = TenantRepository()
        self.ia_repo = IAMasterRepository()

    def provision_client(self, db: Session, request: ClientProvisionRequest) -> dict:
        # 1. Check if email exists
        if self.user_repo.get_by_email(db, request.email):
            raise HTTPException(status_code=400, detail="Email already registered to an account")

        # 2. Create the new Tenant (Company) with billing info
        tenant = self.tenant_repo.create(
            db, 
            name=request.company_name,
            subdomain=request.subdomain,
            pricing_model=request.pricing_model,
            billing_mode=request.billing_mode,
            plan_expiry_date=request.plan_expiry_date,
            max_client_permit=request.max_client_permit
        )

        # 3. Create the IA Master record for registration info
        ia_data = {
            "tenant_id": tenant.id,
            "name_of_ia": tenant.name,
            "name_of_entity": tenant.name,
            "nature_of_entity": request.nature_of_entity,
            "ia_registration_number": request.registration_no,
            "date_of_registration": request.registration_date,
            "date_of_registration_expiry": request.license_expiry_date,
            "registered_email_id": request.email,
            "is_renewal": request.is_renewal,
            "renewal_certificate_no": request.renewal_certificate_no,
            "renewal_expiry_date": request.renewal_expiry_date,
            "relationship_manager_id": request.relationship_manager_id,
            "date_of_birth": request.date_of_birth,
            "registered_address": request.registered_address,
            "registered_contact_number": request.registered_contact_number,
            "office_contact_number": request.office_contact_number,
            "cin_number": request.cin_number,
            "bank_account_number": request.bank_account_number,
            "bank_name": request.bank_name,
            "bank_branch": request.bank_branch,
            "ifsc_code": request.ifsc_code
        }
        db_ia = self.ia_repo.create(db, ia_data)

        # 4. Create Contact Persons
        for cp in request.contact_persons:
            cp_data = {
                "ia_master_id": db_ia.id,
                **cp.dict()
            }
            self.ia_repo.create_contact_person(db, cp_data)

        # 5. The Root User (Owner) is intentionally NOT saved to the Master DB 'users' table anymore.
        # They will only exist natively inside the isolated Bridge Silo via the bridge integration flow.
        
        db.commit()
        db.refresh(tenant)
        db.refresh(db_ia)
        
        return {
            "id": None, # Decoupled from Master users table
            "email": request.email,
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "subdomain": tenant.subdomain,
            "bridge_registration_token": tenant.bridge_registration_token,
            "message": "Client provisioned successfully with full registration and billing profile."
        }

    # --- Staff Management ---
    def list_staff(self, db: Session, tenant_id: any) -> list[dict]:
        from app.models.staff_profile import StaffProfile
        
        # We use outerjoin to include the Owner (who may not have a dedicated StaffProfile yet)
        results = (
            db.query(User, StaffProfile)
            .outerjoin(StaffProfile, User.id == StaffProfile.user_id)
            .filter(
                User.tenant_id == tenant_id,
                User.role.in_(["owner", "partner", "ia_staff", "research_analyst", "investment_advisor", "management", "staff", "relationship_manager"])
            )
            .all()
        )
        
        staff_list = []
        for user, profile in results:
            # For owners/users without profiles, provide sensible fallbacks
            full_name = profile.full_name if profile else user.email.split('@')[0].capitalize()
            designation = profile.designation if profile else ("Principal Officer" if user.role == 'owner' else "Staff Member")
            
            staff_list.append({
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "full_name": full_name or "System User",
                "phone_number": (profile.phone_number if profile else user.phone_number) or "N/A",
                "designation": designation,
                "address": profile.address if profile else None,
                "last_login_at": user.last_login_at,
                "created_at": user.created_at
            })
        return staff_list

    def create_staff_user(self, db: Session, admin: User, request: dict, ip_address: str = None):
        from app.models.tenant import Tenant
        from app.models.staff_profile import StaffProfile
        from app.core.security import get_password_hash
        
        # 1. Create User (Authentication)
        new_user = User(
            tenant_id=admin.tenant_id, # Assumes staff belong to the same tenant as the provisioner
            email=request["email"],
            email_normalized=request["email"].lower(),
            password_hash=get_password_hash(request["password"]),
            role=request["role"],
            status="active"
        )
        db.add(new_user)
        db.flush() # Get user ID
        
        # 2. Create Staff Profile
        new_profile = StaffProfile(
            user_id=new_user.id,
            full_name=request["full_name"],
            phone_number=request["phone_number"],
            designation=request.get("designation"),
            address=request.get("address")
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_profile)
        
        self.log_activity(db, admin, "CREATE_STAFF", "user", str(new_user.id), f"Created staff profile for {new_user.email}", ip_address)
        
        # Return merged data for API response
        return self.list_staff(db, admin.tenant_id)[-1] # Quickest way to get the output schema formatted correctly

    def update_staff_user(self, db: Session, admin: User, user_id: str, request: dict, ip_address: str = None):
        import uuid
        from app.models.staff_profile import StaffProfile
        
        user = self.user_repo.get_by_id(db, uuid.UUID(user_id))
        if not user:
            raise HTTPException(404, "User not found")
        
        profile = db.query(StaffProfile).filter(StaffProfile.user_id == user.id).first()
        
        # Update User fields
        if "role" in request: user.role = request["role"]
        if "status" in request: user.status = request["status"]
            
        # Update Profile fields
        if profile:
            if "full_name" in request: profile.full_name = request["full_name"]
            if "phone_number" in request: profile.phone_number = request["phone_number"]
            if "designation" in request: profile.designation = request["designation"]
            if "address" in request: profile.address = request["address"]
            
        db.commit()
        self.log_activity(db, admin, "UPDATE_STAFF", "user", str(user.id), f"Updated staff details for {user.email}", ip_address)
        
        # Fetch fresh data using UUID object
        results = db.query(User, StaffProfile).join(StaffProfile, User.id == StaffProfile.user_id).filter(User.id == user.id).first()
        user, profile = results
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "full_name": profile.full_name,
            "phone_number": profile.phone_number,
            "designation": profile.designation,
            "address": profile.address,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at
        }

    # --- Activity Logging ---
    def log_activity(self, db: Session, admin: User, action: str, target_type: str, target_id: str = None, details: str = None, ip_address: str = None):
        from app.models.admin_activity_log import AdminActivityLog
        log = AdminActivityLog(
            admin_id=admin.id,
            admin_email=admin.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()

    def get_logs(self, db: Session, limit: int = 100) -> list:
        from app.models.admin_activity_log import AdminActivityLog
        return db.query(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(limit).all()
