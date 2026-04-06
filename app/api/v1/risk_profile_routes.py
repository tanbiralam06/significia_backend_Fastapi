"""
Risk Profile Routes — Bridge Architecture
──────────────────────────────────────────
Risk assessments are now managed through the Bridge.
The scoring calculation logic remains on the backend (it's pure math, no DB needed).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import asyncio

from app.api.deps import get_bridge_client, get_db
from app.services.bridge_client import BridgeClient
from app.services.report_service import ReportService

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

router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES (no connector_id)
# ════════════════════════════════════════════════════════════════════

@router.post("/bridge/calculate", response_model=RiskAssessmentCalculateResponse)
def calculate_risk_profile_bridge(
    payload: RiskAssessmentCalculateRequest,
):
    """
    Dry-run calculation. This is pure math — no Bridge call needed.
    """
    total_score, question_scores = RiskProfileService.calculate_scores(payload.answers)
    risk_tier, recommendation = RiskProfileService.determine_risk_tier(total_score)
    return {
        "success": True,
        "total_score": total_score,
        "question_scores": question_scores,
        "risk_tier": risk_tier,
        "recommendation": recommendation
    }


@router.post("/bridge/save", response_model=dict)
async def save_risk_assessment_bridge(
    payload: RiskAssessmentCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Save a risk assessment via the Bridge."""
    # 1. Resolve client_code to client_id from Bridge
    client = await bridge.get(f"/clients/code/{payload.client_code}")
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in Bridge")
        
    client_id = client.get("id")
    if not client_id:
        raise HTTPException(status_code=500, detail="Bridge client record is missing a valid ID")

    # 2. Calculate score on the backend (it's business logic, not data)
    total_score, question_scores = RiskProfileService.calculate_scores(payload.answers)
    risk_tier, recommendation = RiskProfileService.determine_risk_tier(total_score)

    data = {
        "client_id": client_id,
        "q1_interest_choice": payload.answers.q1,
        "q2_importance_factors": payload.answers.q2.model_dump(),
        "q3_probability_bet": payload.answers.q3,
        "q4_portfolio_choice": payload.answers.q4,
        "q5_loss_behavior": payload.answers.q5,
        "q6_market_reaction": payload.answers.q6,
        "q7_fund_selection": payload.answers.q7,
        "q8_experience_level": payload.answers.q8,
        "q9_time_horizon": payload.answers.q9,
        "q10_net_worth": payload.answers.q10,
        "q11_age_range": payload.answers.q11,
        "q12_income_range": payload.answers.q12,
        "q13_expense_range": payload.answers.q13,
        "q14_dependents": payload.answers.q14,
        "q15_active_loan": payload.answers.q15,
        "q16_investment_objective": payload.answers.q16,
        "calculated_score": total_score,
        "question_scores": question_scores,
        "assigned_risk_tier": risk_tier,
        "tier_recommendation": recommendation,
        "disclaimer_text": payload.disclaimer_text,
        "discussion_notes": payload.discussion_notes,
        "form_name": payload.form_name,
    }
    return await bridge.post("/risk-assessments", data)


@router.get("/bridge/assessments")
@router.get("/bridge/assessments/{client_id}", response_model=list)
async def get_risk_assessments_bridge(
    client_id: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get risk assessments for a client via the Bridge."""
    path = f"/risk-assessments/{client_id}" if client_id else "/risk-assessments"
    return await bridge.get(path)


@router.get("/bridge/questionnaires", response_model=list)
async def list_questionnaires_bridge(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """List all risk questionnaires via the Bridge."""
    return await bridge.get("/risk-questionnaires")


@router.post("/bridge/questionnaires", response_model=dict)
async def create_questionnaire_bridge(
    payload: RiskQuestionnaireCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Create a risk questionnaire via the Bridge."""
    return await bridge.post("/risk-questionnaires", payload.model_dump())


@router.get("/bridge/questionnaires/{q_id}", response_model=dict)
async def get_questionnaire_bridge(
    q_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a risk questionnaire by ID via the Bridge."""
    return await bridge.get(f"/risk-questionnaires/{q_id}")


@router.put("/bridge/questionnaires/{q_id}", response_model=dict)
async def update_questionnaire_bridge(
    q_id: str,
    payload: RiskQuestionnaireUpdate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Update a risk questionnaire via the Bridge."""
    return await bridge.patch(f"/risk-questionnaires/{q_id}", payload.model_dump(exclude_unset=True))


@router.post("/bridge/custom-save", response_model=dict)
async def save_custom_risk_assessment_bridge(
    payload: CustomRiskAssessmentCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Save a custom risk assessment via the Bridge."""
    # 1. Resolve Client
    client = await bridge.get(f"/clients/code/{payload.client_code}")
    client_id = client.get("id")
    if not client_id:
        raise HTTPException(status_code=404, detail=f"Client with code {payload.client_code} not found in Bridge")

    # 2. Fetch Questionnaire for scoring rules
    questionnaire = await bridge.get(f"/risk-questionnaires/{payload.questionnaire_id}")
    if not questionnaire:
        raise HTTPException(status_code=404, detail="Questionnaire not found in Bridge")

    # 3. Calculate scores (Business Logic)
    from app.services.risk_profile_service import RiskProfileService
    total_score, category_name = RiskProfileService.calculate_custom_scores(payload.responses, questionnaire)

    # 4. Prepare Bridge payload
    data = {
        "client_id": client_id,
        "questionnaire_id": str(payload.questionnaire_id),
        "portfolio_name": questionnaire.get("portfolio_name"),
        "category_name": category_name,
        "total_score": total_score,
        "responses": payload.responses,
        "discussion_notes": payload.discussion_notes
    }

    return await bridge.post("/custom-risk-assessments", data)


@router.get("/bridge/custom-assessments")
@router.get("/bridge/custom-assessments/{client_id}", response_model=list)
async def get_custom_assessments_bridge(
    client_id: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get custom risk assessments for a client via the Bridge."""
    path = f"/custom-risk-assessments/{client_id}" if client_id else "/custom-risk-assessments"
    return await bridge.get(path)


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED PDF/DOCX REPORTS
# ════════════════════════════════════════════════════════════════════

@router.get("/bridge/questionnaires/{q_id}/pdf")
async def download_blank_risk_form_bridge(
    q_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
):
    """Download a blank risk profile form via the Bridge."""
    try:
        # 1. Fetch IA Master and Questionnaire info from Bridge
        ia_data = await bridge.get("/ia-master")
        q_data = await bridge.get(f"/risk-questionnaires/{q_id}")
        
        # 2. Resolve Logo from Bridge storage
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                signed_url = url_resp.get("url")
                if signed_url:
                    logo_path = await resolve_logo_to_local_path(signed_url, db)
            except Exception as e:
                import logging
                logging.getLogger("significia.risk").warning(f"Failed to resolve IA logo for risk form: {e}")

        # 3. Generate PDF
        pdf_buffer = ReportService.generate_blank_risk_form_pdf(
            db=db,
            questionnaire_id=q_id,
            ia_logo_override=logo_path,
            ia_data=ia_data,
            questionnaire_data=q_data
        )

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Risk_Assessment_Form_{q_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate blank form: {str(e)}")


@router.get("/bridge/assessment/{assessment_id}/pdf")
async def download_risk_assessment_pdf_bridge(
    assessment_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
):
    """Download a completed risk assessment as PDF via the Bridge."""
    try:
        # 1. Fetch assessment data from Bridge
        assessment = await bridge.get(f"/risk-assessments/id/{assessment_id}")
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        # 2. Fetch Client and IA data in parallel
        client_id = assessment.get("client_id")
        client_task = bridge.get(f"/clients/{client_id}")
        ia_task = bridge.get("/ia-master")
        
        client_data, ia_data = await asyncio.gather(client_task, ia_task)

        # 3. Resolve Logo
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                logo_path = await resolve_logo_to_local_path(url_resp.get("url"), db)
            except: pass

        # 4. Generate PDF
        pdf_buffer = ReportService.generate_risk_profile_pdf_bridge(
            assessment_data=assessment,
            client_data=client_data,
            ia_data=ia_data,
            ia_logo_override=logo_path
        )

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Risk_Assessment_{client_data.get('client_name', 'Client')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.get("/bridge/assessment/{assessment_id}/docx")
async def download_risk_assessment_docx_bridge(
    assessment_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
):
    """Download a completed risk assessment as DOCX via the Bridge."""
    try:
        assessment = await bridge.get(f"/risk-assessments/id/{assessment_id}")
        client_data = await bridge.get(f"/clients/{assessment.get('client_id')}")
        ia_data = await bridge.get("/ia-master")

        # Resolve Logo
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                logo_path = await resolve_logo_to_local_path(url_resp.get("url"), db)
            except: pass

        docx_buffer = ReportService.generate_risk_profile_docx_bridge(
            assessment_data=assessment,
            client_data=client_data,
            ia_data=ia_data,
            ia_logo_override=logo_path
        )

        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Risk_Assessment_{client_data.get('client_name', 'Client')}.docx"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DOCX: {str(e)}")


@router.get("/bridge/custom-assessment/{assessment_id}/pdf")
async def download_custom_risk_assessment_pdf_bridge(
    assessment_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
):
    """Download a completed CUSTOM risk assessment as PDF via the Bridge."""
    try:
        # 1. Fetch assessment data from Bridge
        assessment = await bridge.get(f"/custom-risk-assessments/id/{assessment_id}")
        if not assessment:
            raise HTTPException(status_code=404, detail="Custom Assessment not found")
        
        # 2. Fetch Questionnaire, Client and IA data
        q_id = assessment.get("questionnaire_id")
        client_id = assessment.get("client_id")
        
        client_task = bridge.get(f"/clients/{client_id}")
        ia_task = bridge.get("/ia-master")
        q_task = bridge.get(f"/risk-questionnaires/{q_id}")
        
        client_data, ia_data, q_data = await asyncio.gather(client_task, ia_task, q_task)

        # 3. Resolve Logo
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                logo_path = await resolve_logo_to_local_path(url_resp.get("url"), db)
            except: pass

        # 4. Generate PDF
        pdf_buffer = ReportService.generate_risk_profile_pdf_bridge(
            assessment_data=assessment,
            client_data=client_data,
            ia_data=ia_data,
            ia_logo_override=logo_path,
            questionnaire_data=q_data
        )

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Custom_Risk_Assessment_{client_data.get('client_name', 'Client')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.get("/bridge/custom-assessment/{assessment_id}/docx")
async def download_custom_risk_assessment_docx_bridge(
    assessment_id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
    db: Session = Depends(get_db),
):
    """Download a completed CUSTOM risk assessment as Word via the Bridge."""
    try:
        # 1. Fetch assessment data from Bridge
        assessment = await bridge.get(f"/custom-risk-assessments/id/{assessment_id}")
        if not assessment:
            raise HTTPException(status_code=404, detail="Custom Assessment not found")
        
        # 2. Fetch Questionnaire, Client and IA data
        q_id = assessment.get("questionnaire_id")
        client_id = assessment.get("client_id")
        
        client_task = bridge.get(f"/clients/{client_id}")
        ia_task = bridge.get("/ia-master")
        q_task = bridge.get(f"/risk-questionnaires/{q_id}")
        
        client_data, ia_data, q_data = await asyncio.gather(client_task, ia_task, q_task)

        # 3. Resolve Logo
        logo_path = None
        ia_logo_key = ia_data.get("ia_logo_path")
        if ia_logo_key:
            try:
                from app.utils.file_utils import resolve_logo_to_local_path
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_key})
                logo_path = await resolve_logo_to_local_path(url_resp.get("url"), db)
            except: pass

        # 4. Generate Word
        docx_buffer = ReportService.generate_risk_profile_docx_bridge(
            assessment_data=assessment,
            client_data=client_data,
            ia_data=ia_data,
            ia_logo_override=logo_path,
            questionnaire_data=q_data
        )

        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Custom_Risk_Assessment_{client_data.get('client_name', 'Client')}.docx"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Word: {str(e)}")
