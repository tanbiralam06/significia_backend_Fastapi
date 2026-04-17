from fastapi import APIRouter, Depends, HTTPException, Form, Request
import logging
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_ia_admin
from app.models.user import User
from app.api.deps import get_bridge_client
from app.services.bridge_client import BridgeClient

router = APIRouter()
logger = logging.getLogger("significia.departments")

@router.get("")
async def list_departments(
    current_admin: User = Depends(get_current_ia_admin),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    List all organizational departments.
    Fetched from the Bridge Silo.
    """
    return await bridge.get("/departments")

@router.post("")
async def create_department(
    dept_in: dict,
    current_admin: User = Depends(get_current_ia_admin),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    Add a new department to the IA's organization.
    Synchronized to the Bridge Silo.
    """
    logger.info(f"Creating department with data: {dept_in}")
    return await bridge.post("/departments", data=dept_in)

@router.put("/{dept_id}")
async def update_department(
    dept_id: str,
    dept_in: dict,
    current_admin: User = Depends(get_current_ia_admin),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    Update a department (e.g., rename it).
    """
    return await bridge.put(f"/departments/{dept_id}", data=dept_in)

@router.delete("/{dept_id}")
async def delete_department(
    dept_id: str,
    current_admin: User = Depends(get_current_ia_admin),
    bridge: BridgeClient = Depends(get_bridge_client)
):
    """
    Remove a department.
    """
    return await bridge.delete(f"/departments/{dept_id}")
