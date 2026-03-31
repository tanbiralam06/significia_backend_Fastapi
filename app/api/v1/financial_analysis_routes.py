"""
Financial Analysis API Routes — Bridge Architecture
───────────────────────────────────────────────────
Financial analysis endpoints now support Bridge-powered routes.
"""
import os
import uuid
import tempfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_bridge_client
from app.services.bridge_client import BridgeClient

# Legacy imports
from app.database.remote_session import get_remote_session
from app.schemas.financial_analysis_schema import (
    FinancialAnalysisCreate,
    FinancialAnalysisResponse,
    FinancialAnalysisSummary,
    CalculationDetailsResponse,
)
from app.services.financial_analysis_service import FinancialAnalysisService
from app.utils.financial_report_generator import FinancialReportGenerator
from app.utils.file_utils import resolve_logo_to_local_path
from app.models.ia_master import IAMaster
from app.models.client import ClientProfile
from app.models.financial_analysis import FinancialAnalysisProfile

router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES (no connector_id)
# ════════════════════════════════════════════════════════════════════

@router.post("/bridge/analysis", response_model=dict)
async def create_analysis_bridge(
    analysis_in: FinancialAnalysisCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Create a new financial analysis via the Bridge."""
    return await bridge.post("/api/financial-analysis/profiles", analysis_in.model_dump())


@router.get("/bridge/analysis", response_model=list)
async def list_analyses_bridge(
    client_id: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """List all financial analyses via the Bridge."""
    params = {}
    if client_id:
        params["client_id"] = client_id
    return await bridge.get("/api/financial-analysis/profiles/" + (client_id or ""), params=params)


@router.get("/bridge/analysis/{result_id}", response_model=dict)
async def get_analysis_bridge(
    result_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a financial analysis result by ID via the Bridge."""
    return await bridge.get(f"/api/financial-analysis/results/{result_id}")


# ════════════════════════════════════════════════════════════════════
#  LEGACY ROUTES (with connector_id — kept during transition)
# ════════════════════════════════════════════════════════════════════

@router.get("/{connector_id}/analysis/{result_id}/pdf")
async def download_pdf(
    connector_id: uuid.UUID,
    result_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Download financial analysis report as PDF."""
    result = FinancialAnalysisService.get_analysis(remote_db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    
    profile = remote_db.query(FinancialAnalysisProfile).filter(
        FinancialAnalysisProfile.id == result.profile_id
    ).first()
    client = remote_db.query(ClientProfile).filter(ClientProfile.id == result.client_id).first()
    
    ia_logo_path = None
    ia_master = remote_db.query(IAMaster).first()
    if ia_master:
        ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)

    pdf_stream = FinancialReportGenerator.generate_pdf(
        result=result,
        profile=profile,
        client_name=client.client_name if client else "Client",
        ia_logo_path=ia_logo_path
    )
    
    filename = f"Financial_Analysis_{result_id}.pdf"
    return Response(
        content=pdf_stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{connector_id}/analysis/{result_id}/word")
async def download_word(
    connector_id: uuid.UUID,
    result_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Download financial analysis report as Word document."""
    result = FinancialAnalysisService.get_analysis(remote_db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    
    profile = remote_db.query(FinancialAnalysisProfile).filter(
        FinancialAnalysisProfile.id == result.profile_id
    ).first()
    client = remote_db.query(ClientProfile).filter(ClientProfile.id == result.client_id).first()
    
    ia_logo_path = None
    ia_master = remote_db.query(IAMaster).first()
    if ia_master:
        ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)

    doc_stream = FinancialReportGenerator.generate_docx(
        result=result,
        profile=profile,
        client_name=client.client_name if client else "Client",
        ia_logo_path=ia_logo_path
    )
    
    filename = f"Financial_Analysis_{result_id}.docx"
    return Response(
        content=doc_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{connector_id}/analysis", response_model=FinancialAnalysisResponse)
def create_analysis(
    connector_id: uuid.UUID,
    analysis_in: FinancialAnalysisCreate,
    remote_db: Session = Depends(get_remote_session),
):
    """Create a new financial analysis for a client."""
    try:
        result = FinancialAnalysisService.create_analysis(remote_db, analysis_in)
        return FinancialAnalysisResponse(
            id=result.id,
            profile_id=result.profile_id,
            client_id=result.client_id,
            calculations=result.calculations,
            hlv_data=result.hlv_data,
            medical_data=result.medical_data,
            cash_flow_analysis=result.cash_flow_analysis,
            ai_analysis=result.ai_analysis,
            financial_health_score=result.financial_health_score,
            created_at=result.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{connector_id}/analysis", response_model=List[FinancialAnalysisSummary])
def list_analyses(
    connector_id: uuid.UUID,
    client_id: Optional[uuid.UUID] = Query(None),
    remote_db: Session = Depends(get_remote_session),
):
    """List all financial analyses, optionally filtered by client_id."""
    return FinancialAnalysisService.list_analyses(remote_db, client_id)


@router.get("/{connector_id}/analysis/{result_id}", response_model=FinancialAnalysisResponse)
def get_analysis(
    connector_id: uuid.UUID,
    result_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Get a specific financial analysis result."""
    result = FinancialAnalysisService.get_analysis(remote_db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return FinancialAnalysisResponse(
        id=result.id,
        profile_id=result.profile_id,
        client_id=result.client_id,
        calculations=result.calculations,
        hlv_data=result.hlv_data,
        medical_data=result.medical_data,
        cash_flow_analysis=result.cash_flow_analysis,
        ai_analysis=result.ai_analysis,
        financial_health_score=result.financial_health_score,
        created_at=result.created_at,
    )


@router.get("/{connector_id}/analysis/{result_id}/details", response_model=CalculationDetailsResponse)
def get_calculation_details(
    connector_id: uuid.UUID,
    result_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Get step-by-step calculation breakdown for a financial analysis."""
    details = FinancialAnalysisService.get_calculation_details(remote_db, result_id)
    if not details:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return details


@router.get("/{connector_id}/form")
async def download_blank_form(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Download a blank financial analysis data entry form as PDF."""
    ia_logo_path = None
    ia_master = remote_db.query(IAMaster).first()
    if ia_master:
        ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)

    pdf_stream = FinancialReportGenerator.generate_blank_form(ia_logo_path=ia_logo_path)
    
    filename = "Financial_Analysis_Data_Entry_Form.pdf"
    return Response(
        content=pdf_stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{connector_id}/analysis/client/{client_id}", response_model=FinancialAnalysisResponse)
def get_latest_analysis_for_client(
    connector_id: uuid.UUID,
    client_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session),
):
    """Get the latest financial analysis for a specific client."""
    result = FinancialAnalysisService.get_analysis_by_client(remote_db, client_id)
    if not result:
        raise HTTPException(status_code=404, detail="No analysis found for this client")
    return FinancialAnalysisResponse(
        id=result.id,
        profile_id=result.profile_id,
        client_id=result.client_id,
        calculations=result.calculations,
        hlv_data=result.hlv_data,
        medical_data=result.medical_data,
        cash_flow_analysis=result.cash_flow_analysis,
        ai_analysis=result.ai_analysis,
        financial_health_score=result.financial_health_score,
        created_at=result.created_at,
    )
