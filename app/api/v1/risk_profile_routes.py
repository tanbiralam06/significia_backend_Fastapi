from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database.remote_session import get_remote_session
from app.schemas.risk_profile_schema import (
    RiskAssessmentCreate, 
    RiskAssessmentCalculateRequest, 
    RiskAssessmentCalculateResponse,
    SaveAssessmentResponse,
    RiskAssessmentResponse
)
from app.schemas.custom_risk_profile_schema import (
    RiskQuestionnaireCreate,
    RiskQuestionnaireUpdate,
    RiskQuestionnaireResponse,
    CustomRiskAssessmentCreate,
    CustomRiskAssessmentResponse
)
from app.services.risk_profile_service import RiskProfileService
from app.services.custom_risk_profile_service import CustomRiskProfileService
from app.models.risk_profile import RiskAssessment
from app.models.client import ClientProfile
from app.models.ia_master import IAMaster
from app.utils.file_utils import resolve_logo_to_local_path
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
async def download_risk_profile_pdf(
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
        
        # Resolve IA logo path if available
        ia_logo_path = None
        ia_master = remote_db.execute(select(IAMaster)).first()
        if ia_master:
            ia_master = ia_master[0]
            ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
        
        pdf_buffer = ReportService.generate_risk_profile_pdf(remote_db, assessment_id, ia_logo_path)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Risk_Assessment_{assessment_id}.pdf"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.get("/{connector_id}/assessment/{assessment_id}/docx")
async def download_risk_profile_docx(
    connector_id: uuid.UUID,
    assessment_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a DOCX report for a specific risk assessment.
    """
    try:
        from app.services.report_service import ReportService
        from fastapi.responses import StreamingResponse
        
        # Resolve IA logo path if available
        ia_logo_path = None
        ia_master = remote_db.execute(select(IAMaster)).first()
        if ia_master:
            ia_master = ia_master[0]
            ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
            
        docx_buffer = ReportService.generate_risk_profile_docx(remote_db, assessment_id, ia_logo_path)
        
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Risk_Assessment_{assessment_id}.docx"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DOCX: {str(e)}")

@router.get("/{connector_id}/assessments", response_model=List[RiskAssessmentResponse])
def list_risk_assessments(
    connector_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Get all risk assessments for this connector.
    """
    try:
        assessments = RiskProfileService.list_assessments(remote_db)
        return assessments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch assessments: {str(e)}")

# --- Custom Risk Questionnaire Endpoints ---

@router.post("/{connector_id}/questionnaires", response_model=RiskQuestionnaireResponse)
def create_questionnaire(
    connector_id: uuid.UUID,
    payload: RiskQuestionnaireCreate,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        return CustomRiskProfileService.create_questionnaire(remote_db, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{connector_id}/questionnaires", response_model=List[RiskQuestionnaireResponse])
def list_questionnaires(
    connector_id: uuid.UUID,
    status: Optional[str] = None,
    remote_db: Session = Depends(get_remote_session)
):
    return CustomRiskProfileService.list_questionnaires(remote_db, status)

@router.get("/{connector_id}/questionnaires/{q_id}", response_model=RiskQuestionnaireResponse)
def get_questionnaire(
    connector_id: uuid.UUID,
    q_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    q = CustomRiskProfileService.get_questionnaire(remote_db, q_id)
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return q

@router.put("/{connector_id}/questionnaires/{q_id}", response_model=RiskQuestionnaireResponse)
def update_questionnaire(
    connector_id: uuid.UUID,
    q_id: uuid.UUID,
    payload: RiskQuestionnaireUpdate,
    remote_db: Session = Depends(get_remote_session)
):
    q = CustomRiskProfileService.update_questionnaire(remote_db, q_id, payload)
    if not q:
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    return q

@router.post("/{connector_id}/custom-save", response_model=CustomRiskAssessmentResponse)
def save_custom_risk_assessment(
    connector_id: uuid.UUID,
    request: Request,
    payload: CustomRiskAssessmentCreate,
    remote_db: Session = Depends(get_remote_session)
):
    try:
        user_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "Unknown")
        return CustomRiskProfileService.submit_assessment(remote_db, payload, user_ip, user_agent)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{connector_id}/custom-assessments", response_model=List[CustomRiskAssessmentResponse])
def list_custom_assessments(
    connector_id: uuid.UUID,
    client_id: Optional[uuid.UUID] = None,
    remote_db: Session = Depends(get_remote_session)
):
    return CustomRiskProfileService.list_client_assessments(remote_db, client_id)
    
@router.get("/{connector_id}/custom-assessment/{assessment_id}/pdf")
async def download_custom_risk_profile_pdf(
    connector_id: uuid.UUID,
    assessment_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a PDF report for a custom risk assessment.
    """
    try:
        from app.services.report_service import ReportService
        from fastapi.responses import StreamingResponse
        
        ia_logo_path = None
        ia_master = remote_db.execute(select(IAMaster)).first()
        if ia_master:
            ia_master = ia_master[0]
            ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
        
        pdf_buffer = ReportService.generate_custom_risk_profile_pdf(remote_db, assessment_id, ia_logo_path)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Custom_Risk_Assessment_{assessment_id}.pdf"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate custom PDF: {str(e)}")

@router.get("/{connector_id}/custom-assessment/{assessment_id}/docx")
async def download_custom_risk_profile_docx(
    connector_id: uuid.UUID,
    assessment_id: uuid.UUID,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate and download a DOCX report for a custom risk assessment.
    """
    try:
        from app.services.report_service import ReportService
        from fastapi.responses import StreamingResponse
        
        ia_logo_path = None
        ia_master = remote_db.execute(select(IAMaster)).first()
        if ia_master:
            ia_master = ia_master[0]
            ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
            
        docx_buffer = ReportService.generate_custom_risk_profile_docx(remote_db, assessment_id, ia_logo_path)
        
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Custom_Risk_Assessment_{assessment_id}.docx"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate custom DOCX: {str(e)}")

@router.get("/{connector_id}/questionnaires/{questionnaire_id}/pdf")
async def download_blank_risk_profile_pdf(
    connector_id: uuid.UUID,
    questionnaire_id: str,
    remote_db: Session = Depends(get_remote_session)
):
    """
    Generate a blank, printable PDF for a custom risk questionnaire.
    """
    try:
        from app.services.report_service import ReportService
        from fastapi.responses import StreamingResponse
        
        ia_logo_path = None
        ia_master = remote_db.execute(select(IAMaster)).first()
        if ia_master:
            ia_master = ia_master[0]
            # Try to resolve logo to a local path for ReportLab
            try:
                ia_logo_path = await resolve_logo_to_local_path(ia_master.ia_logo_path, remote_db)
            except:
                ia_logo_path = None
            
        pdf_buffer = ReportService.generate_blank_risk_form_pdf(remote_db, questionnaire_id, ia_logo_path)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Blank_Risk_Form_{questionnaire_id}.pdf"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate blank PDF: {str(e)}")
