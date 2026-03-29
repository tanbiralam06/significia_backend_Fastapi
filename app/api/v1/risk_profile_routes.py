import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from app.database.remote_session import get_remote_session
from app.schemas.risk_profile_schema import (
    RiskAssessmentCreate, 
    RiskAssessmentCalculateRequest, 
    RiskAssessmentCalculateResponse,
    SaveAssessmentResponse,
    RiskAssessmentResponse
)
from app.services.risk_profile_service import RiskProfileService
from app.models.risk_profile import RiskAssessment
from app.models.client import ClientProfile
from sqlalchemy import select

router = APIRouter()

@router.post("/{connector_id}/calculate", response_model=RiskAssessmentCalculateResponse)
def calculate_risk_profile(
    connector_id: uuid.UUID,
    payload: RiskAssessmentCalculateRequest,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Dry-run calculation of risk score and tier based on provided answers.
    """
    try:
        total_score, question_scores = RiskProfileService.calculate_scores(payload.answers)
        risk_tier, recommendation = RiskProfileService.determine_risk_tier(total_score)
        
        return {
            "success": True,
            "total_score": total_score,
            "question_scores": question_scores,
            "risk_tier": risk_tier,
            "recommendation": recommendation
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{connector_id}/save", response_model=SaveAssessmentResponse)
def save_risk_assessment(
    connector_id: uuid.UUID,
    request: Request,
    payload: RiskAssessmentCreate,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Persist a risk assessment record and update the client's risk master profile.
    """
    try:
        user_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        assessment_id, risk_id, total_score, risk_tier, client_code, ia_reg = RiskProfileService.save_assessment(
            remote_db, payload, user_ip, user_agent
        )
        
        return {
            "success": True,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "total_score": total_score,
            "risk_tier": risk_tier,
            "client_code": client_code,
            "ia_registration_number": ia_reg
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save assessment: {str(e)}")

@router.get("/{connector_id}/client/{client_code}/latest", response_model=RiskAssessmentResponse)
def get_latest_risk_assessment(
    connector_id: uuid.UUID,
    client_code: str,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Fetch the most recent risk assessment for a specific client code.
    """
    # Find client first
    client = remote_db.execute(
        select(ClientProfile).where(ClientProfile.client_code == client_code)
    ).scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get latest assessment
    assessment = remote_db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.client_id == client.id)
        .order_by(RiskAssessment.created_at.desc())
    ).first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="No risk assessment found for this client")
        
    return assessment[0]

@router.get("/{connector_id}/assessment/{assessment_id}/pdf")
def download_risk_profile_pdf(
    connector_id: uuid.UUID,
    assessment_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a PDF report for a specific risk assessment.
    """
    try:
        from app.services.report_service import ReportService
        from fastapi.responses import StreamingResponse
        
        pdf_buffer = ReportService.generate_risk_profile_pdf(remote_db, assessment_id)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Risk_Assessment_{assessment_id}.pdf"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
