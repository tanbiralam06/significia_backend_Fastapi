from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database.remote_session import get_remote_session
from app.schemas.asset_allocation import (
    AssetAllocationCreate,
    AssetAllocationResponse,
    ClientValidateResponse,
    AssetAllocationSaveResponse
)
from app.services.asset_allocation_service import AssetAllocationService
from app.models.ia_master import IAMaster
from app.utils.file_utils import resolve_logo_to_local_path
from sqlalchemy import select

router = APIRouter()

@router.post("/{connector_id}/validate-client", response_model=ClientValidateResponse)
def validate_client(
    connector_id: uuid.UUID,
    payload: dict,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Validate client code and return profile/risk data.
    """
    client_code = payload.get("client_code")
    if not client_code:
        raise HTTPException(status_code=400, detail="Client code is required")
        
    result = AssetAllocationService.validate_client_for_allocation(remote_db, client_code)
    return result

@router.post("/{connector_id}/save", response_model=AssetAllocationSaveResponse)
def save_asset_allocation(
    connector_id: uuid.UUID,
    request: Request,
    payload: AssetAllocationCreate,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Persist an asset allocation record.
    """
    from sqlalchemy import text

    # Ensure table exists before saving (idempotent for existing connectors)
    try:
        remote_db.execute(text("""
            CREATE TABLE IF NOT EXISTS significia_core.asset_allocations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
                ia_registration_number VARCHAR(100) NOT NULL,
                assigned_risk_tier VARCHAR(100) NOT NULL,
                tier_recommendation TEXT NOT NULL,
                equities_percentage DOUBLE PRECISION DEFAULT 0.0,
                debt_securities_percentage DOUBLE PRECISION DEFAULT 0.0,
                commodities_percentage DOUBLE PRECISION DEFAULT 0.0,
                stocks_percentage DOUBLE PRECISION DEFAULT 0.0,
                mutual_fund_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
                ulip_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
                fixed_deposits_bonds_percentage DOUBLE PRECISION DEFAULT 0.0,
                mutual_fund_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
                ulip_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
                gold_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
                silver_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
                system_conclusion TEXT,
                generate_system_conclusion BOOLEAN DEFAULT TRUE,
                discussion_notes TEXT,
                disclaimer_text TEXT,
                total_allocation DOUBLE PRECISION DEFAULT 100.0,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        remote_db.commit()
    except Exception:
        remote_db.rollback()

    try:
        user_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        allocation = AssetAllocationService.create_allocation(
            remote_db, payload, user_ip, user_agent
        )
        
        return {
            "success": True,
            "allocation_id": allocation.id,
            "message": "Asset allocation saved successfully"
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save allocation: {str(e)}")

@router.get("/{connector_id}/allocations", response_model=List[AssetAllocationResponse])
def list_allocations(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    List all asset allocations. Auto-creates the table if it does not exist yet
    (for connectors initialized before this feature was added).
    """
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    # Ensure the table exists (idempotent migration for existing connectors)
    try:
        remote_db.execute(text("""
            CREATE TABLE IF NOT EXISTS significia_core.asset_allocations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                client_id UUID NOT NULL REFERENCES significia_core.clients(id) ON DELETE CASCADE,
                ia_registration_number VARCHAR(100) NOT NULL,
                assigned_risk_tier VARCHAR(100) NOT NULL,
                tier_recommendation TEXT NOT NULL,
                equities_percentage DOUBLE PRECISION DEFAULT 0.0,
                debt_securities_percentage DOUBLE PRECISION DEFAULT 0.0,
                commodities_percentage DOUBLE PRECISION DEFAULT 0.0,
                stocks_percentage DOUBLE PRECISION DEFAULT 0.0,
                mutual_fund_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
                ulip_equity_percentage DOUBLE PRECISION DEFAULT 0.0,
                fixed_deposits_bonds_percentage DOUBLE PRECISION DEFAULT 0.0,
                mutual_fund_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
                ulip_debt_percentage DOUBLE PRECISION DEFAULT 0.0,
                gold_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
                silver_etf_percentage DOUBLE PRECISION DEFAULT 0.0,
                system_conclusion TEXT,
                generate_system_conclusion BOOLEAN DEFAULT TRUE,
                discussion_notes TEXT,
                disclaimer_text TEXT,
                total_allocation DOUBLE PRECISION DEFAULT 100.0,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        remote_db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_asset_allocations_client ON significia_core.asset_allocations(client_id);"
        ))
        remote_db.commit()
    except Exception as migration_err:
        remote_db.rollback()
        print(f"[AssetAllocation] Migration warning (non-fatal): {migration_err}")

    try:
        return AssetAllocationService.list_allocations(remote_db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch allocations: {str(e)}")

@router.get("/{connector_id}/allocation/{allocation_id}", response_model=AssetAllocationResponse)
def get_allocation(
    connector_id: uuid.UUID,
    allocation_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Get a specific asset allocation by ID.
    """
    allocation = AssetAllocationService.get_allocation_by_id(remote_db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return allocation

@router.get("/{connector_id}/allocation/{allocation_id}/pdf")
async def download_allocation_pdf(
    connector_id: uuid.UUID,
    allocation_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a PDF report for a specific asset allocation.
    """
    try:
        from app.utils.reports.asset_allocation_report import AssetAllocationReportUtils
        from fastapi.responses import StreamingResponse
        
        allocation = AssetAllocationService.get_allocation_by_id(remote_db, allocation_id)
        if not allocation:
            raise HTTPException(status_code=404, detail="Allocation not found")
            
        ia_master = remote_db.execute(select(IAMaster).where(IAMaster.ia_registration_number == allocation.ia_registration_number)).scalar_one_or_none()
        if not ia_master:
            # Fallback to first IA if specific one not found or lookup failed
            ia_master = remote_db.execute(select(IAMaster)).first()
            if ia_master:
                ia_master = ia_master[0]
        
        ia_logo_path = None
        if ia_master:
            try:
                ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
            except:
                ia_logo_path = None
        
        pdf_buffer = AssetAllocationReportUtils.generate_pdf(allocation, ia_master, ia_logo_path)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Asset_Allocation_{allocation_id}.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.get("/{connector_id}/allocation/{allocation_id}/docx")
async def download_allocation_docx(
    connector_id: uuid.UUID,
    allocation_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a DOCX report for a specific asset allocation.
    """
    try:
        from app.utils.reports.asset_allocation_report import AssetAllocationReportUtils
        from fastapi.responses import StreamingResponse
        
        allocation = AssetAllocationService.get_allocation_by_id(remote_db, allocation_id)
        if not allocation:
            raise HTTPException(status_code=404, detail="Allocation not found")
            
        ia_master = remote_db.execute(select(IAMaster).where(IAMaster.ia_registration_number == allocation.ia_registration_number)).scalar_one_or_none()
        if not ia_master:
            ia_master = remote_db.execute(select(IAMaster)).first()
            if ia_master:
                ia_master = ia_master[0]
        
        docx_buffer = AssetAllocationReportUtils.generate_docx(allocation, ia_master)
        
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Asset_Allocation_{allocation_id}.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DOCX: {str(e)}")
