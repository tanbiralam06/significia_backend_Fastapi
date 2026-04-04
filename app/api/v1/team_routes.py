from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_ia_owner, require_profile_completed
from app.schemas.admin_schema import StaffUserCreate, StaffUserOut, StaffUserUpdate
from app.services.admin_service import AdminService
from app.models.user import User
from app.services.bridge_client import BridgeClient
from app.api.deps import get_bridge_client

router = APIRouter()
admin_service = AdminService()

@router.get("/", response_model=List[StaffUserOut])
async def list_team_members(
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_ia_owner),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    List all team members (Partners, Staff, Analysts) for the current IA's organization.
    Pulled dynamically from the Local Bridge DB to enforce absolute Silo isolation.
    """
    try:
        bridge_staff = await bridge.get("/employees")
        formatted = []
        for emp in bridge_staff:
            formatted.append({
                "id": emp.get("id"),
                "email": emp.get("email"),
                "role": emp.get("role", "staff"),
                "status": "active" if emp.get("is_active") else "inactive",
                "full_name": emp.get("name", "Staff Member"),
                "phone_number": emp.get("phone_number") or "N/A",
                "designation": emp.get("designation") or "Staff",
                "address": None,
                "created_at": emp.get("created_at")
            })
        return formatted
    except Exception as e:
        # Failsafe if Bridge is completely offline
        return []

@router.post("/", response_model=StaffUserOut, status_code=201)
async def onboard_team_member(
    request_data: StaffUserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_ia_owner),
    bridge: BridgeClient = Depends(get_bridge_client),
    # Ensure profile is completed before onboarding others
    _ = Depends(require_profile_completed)
):
    """
    Onboard a new Partner or Staff member.
    The new member will be counted against the organization's 'Internal User' limit.
    """
    # 1. License Check (Internal Users only)
    tenant = current_owner.tenant
    current_usage = db.query(User).filter(
        User.tenant_id == tenant.id,
        User.role.in_(["owner", "partner", "ia_staff", "analyst", "staff"])
    ).count()

    if current_usage >= tenant.max_client_permit:
        raise HTTPException(
            status_code=403,
            detail=f"User limit reached ({tenant.max_client_permit}). Please upgrade your plan to onboard more team members."
        )

    # 2. Prevent IA Owners from creating Super Admins
    if request_data.role not in ["partner", "ia_staff", "analyst"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. You can only onboard Partners, Staff, or Analysts."
        )

    # Mirror the user into the Bridge DB so they can login.
    # We DO NOT save them in the Master Database anymore.
    bridge_payload = {
        "email": request_data.email,
        "name": request_data.full_name,
        "password": request_data.password,
        "role": request_data.role,
        "designation": request_data.designation,
        "phone_number": request_data.phone_number
    }
    
    # Send to silo and expect the bridge to create the user and return their new ID
    bridge_res = await bridge.post("/employees", bridge_payload)
    
    return {
        "id": bridge_res.get("id"),
        "email": request_data.email,
        "role": request_data.role,
        "status": "active",
        "full_name": request_data.full_name,
        "phone_number": request_data.phone_number,
        "designation": request_data.designation,
        "address": None,
        "last_login_at": None,
        "created_at": bridge_res.get("created_at")
    }

@router.put("/{user_id}", response_model=StaffUserOut)
async def update_team_member(
    user_id: UUID,
    request_data: StaffUserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_ia_owner),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    Update a team member's details or role.
    """
    # Sync updates to Bridge DB
    bridge_payload = {}
    if request_data.email is not None: bridge_payload["email"] = request_data.email
    if request_data.full_name is not None: bridge_payload["name"] = request_data.full_name
    if request_data.role is not None: bridge_payload["role"] = request_data.role
    if request_data.status is not None: bridge_payload["status"] = request_data.status
    
    if bridge_payload:
        await bridge.put(f"/employees/{str(user_id)}", json=bridge_payload)

    # Return a mocked StaffUserOut to satisfy the frontend immediately
    return {
        "id": str(user_id),
        "email": request_data.email or "updated@silo",
        "role": request_data.role or "staff",
        "status": request_data.status or "active",
        "full_name": request_data.full_name or "Updated Staff",
        "phone_number": "N/A",
        "designation": "Staff",
        "address": None,
        "last_login_at": None,
        "created_at": None
    }

@router.delete("/{user_id}", status_code=204)
async def remove_team_member(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_owner: User = Depends(get_current_ia_owner),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    Deactivate a team member directly in the silo.
    """
    # Sync deletion (deactivation) to Bridge DB
    await bridge.delete(f"/employees/{str(user_id)}")
    
    return None
