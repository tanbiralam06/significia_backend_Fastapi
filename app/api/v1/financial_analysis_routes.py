"""
Financial Analysis API Routes — Bridge Architecture
───────────────────────────────────────────────────
Financial analysis endpoints now support Bridge-powered routes.
"""
import os
import uuid
import tempfile
import logging
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from types import SimpleNamespace

from app.api.deps import get_bridge_client
from app.services.bridge_client import BridgeClient
from app.analysis.financial_calculator import FinancialCalculator
from app.analysis.ai_commentary import SystemCommentaryGenerator
from app.utils.financial_report_generator import FinancialReportGenerator

from app.schemas.financial_analysis_schema import (
    FinancialAnalysisCreate,
    FinancialAnalysisResponse,
    FinancialAnalysisSummary,
    CalculationDetailsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  BRIDGE-POWERED ROUTES (no connector_id)
# ════════════════════════════════════════════════════════════════════

@router.post("/bridge/analysis", response_model=dict)
async def create_analysis_bridge(
    analysis_in: FinancialAnalysisCreate,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Create a new financial analysis via the Bridge.
    Orchestration: Calculate -> snapshot profile -> save result -> return ID.
    """
    try:
        # 1. Fetch client info from bridge for calculations (need client_name)
        client = await bridge.get(f"/clients/{analysis_in.client_id}")
        if not client:
            raise HTTPException(404, "Client not found in Bridge")
        
        client_name = client.get("client_name", "Valued Client")

        # 2. Perform Calculations (Mirroring FinancialAnalysisService logic)
        client_age = FinancialCalculator.calculate_current_age(analysis_in.dob)
        if client_age is None:
            raise HTTPException(400, "Invalid date of birth. Client must be at least 18 years old.")

        expenses_dict = analysis_in.expenses.model_dump()
        assets_dict = analysis_in.assets.model_dump()
        liabilities_dict = analysis_in.liabilities.model_dump()
        insurance_dict = analysis_in.insurance.model_dump()
        assumptions_dict = analysis_in.assumptions.model_dump()

        total_expenses = analysis_in.expenses.total
        total_assets = analysis_in.assets.total
        total_liabilities = analysis_in.liabilities.total
        net_worth = total_assets - total_liabilities

        calculations = FinancialCalculator.perform_comprehensive_analysis(
            client_age=client_age,
            annual_income=analysis_in.annual_income,
            annual_expenses=total_expenses,
            net_worth=net_worth,
            current_life_cover=insurance_dict.get('life_cover', 0),
            current_medical_cover=insurance_dict.get('med_cover', 0),
            existing_retirement_savings=assets_dict.get('retirement', 0),
            total_assets=total_assets,
            current_liabilities=total_liabilities,
            assumptions=assumptions_dict,
            land_building_value=assets_dict.get('land', 0),
            investments_value=assets_dict.get('inv', 0),
            medical_bonus_years=analysis_in.medical_bonus_years,
            medical_bonus_percentage=analysis_in.medical_bonus_percentage,
            education_investment_pct=analysis_in.education_investment_pct,
            marriage_investment_pct=analysis_in.marriage_investment_pct,
            cash_at_bank=assets_dict.get('cash', 0),
        )

        hlv_data = FinancialCalculator.perform_hlv_calculations(
            client_age=client_age,
            annual_income=analysis_in.annual_income,
            annual_expenses=total_expenses,
            net_worth=net_worth,
            current_life_cover=insurance_dict.get('life_cover', 0),
            total_assets=total_assets,
            current_liabilities=total_liabilities,
            assumptions=assumptions_dict,
            spouse_life_expectancy=assumptions_dict.get('le_spouse', 85),
            land_building_value=assets_dict.get('land', 0),
            allocated_investment_education=assets_dict.get('inv', 0) * (analysis_in.education_investment_pct / 100),
            allocated_investment_marriage=assets_dict.get('inv', 0) * (analysis_in.marriage_investment_pct / 100),
        )

        medical_data = FinancialCalculator.perform_medical_calculations(
            client_age=client_age,
            current_medical_cover=insurance_dict.get('med_cover', 0),
            assumptions=assumptions_dict,
            medical_bonus_years=analysis_in.medical_bonus_years,
            medical_bonus_percentage=analysis_in.medical_bonus_percentage,
        )

        ai_analysis = None
        if not analysis_in.exclude_ai:
            ai_analysis = SystemCommentaryGenerator.generate_all_commentary(
                calculations=calculations,
                hlv_data=hlv_data,
                medical_data=medical_data,
                client_name=client_name,
            )

        cash_flow = calculations.pop('cash_flow_analysis', None)

        # 3. Save Profile Snapshot to Bridge
        profile_data = analysis_in.model_dump()
        # Convert children DOBs to string for JSON
        if "children" in profile_data:
            for child in profile_data["children"]:
                if isinstance(child.get("dob"), (date, date)):
                    child["dob"] = child["dob"].isoformat()

        profile_resp = await bridge.post("/financial-analysis/profiles", profile_data)
        profile_id = profile_resp.get("id")
        if not profile_id:
            raise HTTPException(500, "Failed to create profile in Bridge")

        # 4. Save Analysis Result to Bridge
        result_data = {
            "profile_id": profile_id,
            "client_id": str(analysis_in.client_id),
            "calculations": calculations,
            "hlv_data": hlv_data,
            "medical_data": medical_data,
            "cash_flow_analysis": cash_flow,
            "ai_analysis": ai_analysis,
            "financial_health_score": calculations.get('financial_health_score', 0),
        }
        
        result_resp = await bridge.post("/financial-analysis/results", result_data)
        result_id = result_resp.get("id")
        if not result_id:
            raise HTTPException(500, "Failed to create analysis result in Bridge")

        return {"status": "created", "id": result_id}

    except Exception as e:
        logger.error(f"Error in create_analysis_bridge: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/bridge/analysis", response_model=list)
async def list_analyses_bridge(
    client_id: Optional[str] = None,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """List all financial analyses via the Bridge."""
    params = {}
    if client_id:
        params["client_id"] = client_id
    path = f"/financial-analysis/profiles/{client_id}" if client_id else "/financial-analysis/profiles"
    return await bridge.get(path, params=params)


@router.get("/bridge/analysis/{id}", response_model=dict)
async def get_analysis_bridge(
    id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Get a financial analysis result by Result ID or Profile ID via the Bridge."""
    result, profile = await fetch_analysis_data(id, bridge)
    if not profile:
        raise HTTPException(404, f"Financial profile not found for ID: {id} [DEBUG: UNV_V3]")
        
    if not result:
        # Return a structured empty result to prevent FE 404/crash
        return {
            "id": id,
            "profile_id": id if not result else result.get('profile_id'),
            "calculations": {},
            "hlv_data": {},
            "medical_data": {},
            "financial_health_score": 0,
            "financial_health_score_details": [],
            "status": "INITIAL" # Signal to FE that this is a new profile
        }
        
    return result


def dict_to_obj(d, preserve_keys=None):
    """
    Recursively convert a dictionary to an object with attributes.
    Preserves certain keys as dictionaries if specified (needed for .get() access).
    """
    if preserve_keys is None:
        preserve_keys = {
            'expenses', 'assets', 'liabilities', 'insurance', 'assumptions', 
            'hlv_data', 'calculations', 'medical_data', 'cash_flow_analysis',
            'children', 'others', 'ai_analysis'
        }
        
    if isinstance(d, dict):
        obj = SimpleNamespace()
        for k, v in d.items():
            if k in preserve_keys:
                setattr(obj, k, v)
            else:
                setattr(obj, k, dict_to_obj(v, preserve_keys))
        return obj
    elif isinstance(d, list):
        return [dict_to_obj(i, preserve_keys) for i in d]
    else:
        return d


async def fetch_analysis_data(id: str, bridge: BridgeClient):
    """
    Helper to fetch analysis result and profile.
    Tries resolving the ID as a Result ID first, then as a Profile ID, then as a Client ID.
    """
    result = None
    profile = None

    # 1. Try resolving as a Result ID first
    try:
        result = await bridge.get(f"/financial-analysis/results/id/{id}")
        if result:
            profile = await bridge.get(f"/financial-analysis/profiles/id/{result.get('profile_id')}")
            return result, profile
    except HTTPException as e:
        if e.status_code != 404:
            raise e

    # 2. Try resolving as a Profile ID
    try:
        profile = await bridge.get(f"/financial-analysis/profiles/id/{id}")
    except HTTPException as e:
        if e.status_code != 404:
            raise e
            
    # 3. Try resolving as a Client ID (fetch latest profile for this client)
    if not profile:
        try:
            profiles = await bridge.get(f"/financial-analysis/profiles", params={"client_id": id})
            if profiles and isinstance(profiles, list) and len(profiles) > 0:
                profile = profiles[0] # Take the latest profile
        except HTTPException as e:
            if e.status_code != 404:
                raise e

    if profile:
        profile_id = profile.get('id')
        try:
            results = await bridge.get(f"/financial-analysis/results/{profile_id}")
            if results and isinstance(results, list) and len(results) > 0:
                result = results[0]
        except HTTPException as e:
            if e.status_code != 404:
                raise e
        
        # We found the profile! Return it even if there are no results yet
        return result, profile
    
    return None, None


@router.get("/bridge/analysis/{id}/details", response_model=dict)
async def get_analysis_details_bridge(
    id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """
    Get detailed calculation steps for the analysis result.
    Transforms Bridge data into the format expected by the frontend 'Calculation View'.
    """
    result, profile = await fetch_analysis_data(id, bridge)
    if not profile:
        raise HTTPException(404, "Analysis profile not found")

    if not result:
        return {
            "id": id,
            "profile_id": id,
            "details": [],
            "summary": "No calculations performed yet."
        }

    # Mirroring FinancialAnalysisService.get_calculation_details logic
    calculations = result.get("calculations", {})
    assumptions = profile.get("assumptions", {})
    total_expenses = profile.get("expenses", {}).get("total", 0)
    
    # We reconstruct the 'details' list for the frontend
    details = []
    
    # 1. HLV
    details.append({
        'section': 'Human Life Value (Income Replacement)',
        'steps': [
            {
                'step': 1,
                'description': 'Annual Income to be Replaced',
                'formula': 'Income_Replaced = Annual_Income × SOL_HLV%',
                'calculation': f'Rs {profile.get("annual_income", 0):,} × {assumptions.get("sol_hlv", 70)}%',
                'result': f'Rs {int(profile.get("annual_income", 0) * (assumptions.get("sol_hlv", 70)/100)):,}',
            },
            {
                'step': 2,
                'description': 'Replacement Corpus (PV of Annuity)',
                'formula': 'HLV = Income_Replaced × [(1 - (1+i/1+r)^n) / (r-i)]',
                'calculation': f'Years: {assumptions.get("le_spouse", 85) - FinancialCalculator.calculate_current_age(profile.get("dob"))}',
                'result': f'Total HLV: Rs {result.get("hlv_data", {}).get("hlv_income_method", 0):,}',
            }
        ]
    })

    # 2. Retirement
    e_adjusted = total_expenses * (assumptions.get("sol_ret", 80) / 100)
    years_to_retirement = (assumptions.get("retirement_age", 60) - 
                         FinancialCalculator.calculate_current_age(profile.get("dob")))
    
    details.append({
        'section': 'Retirement Planning',
        'steps': [
            {
                'step': 1,
                'description': 'Inflation-Adjusted Monthly Expenses at Retirement',
                'formula': 'E_retirement = E_today × (1 + i)^n',
                'calculation': f'Today: Rs {int(e_adjusted/12):,} | Inflation: {assumptions.get("inflation", 6)}% | Years: {years_to_retirement}',
                'result': f'Monthly at Retirement: Rs {int(calculations.get("retirement_corpus_at_retirement", 0) / 120):,}' # Approx monthly draw
            },
            {
                'step': 2,
                'description': 'Total Retirement Corpus Required',
                'result': f'Rs {calculations.get("retirement_corpus_at_retirement", 0):,}'
            }
        ]
    })

    # 3. Medical Corpus
    medical_data = result.get("medical_data", {})
    details.append({
        'section': 'Medical Corpus (Post-Retirement)',
        'steps': [
            {
                'step': 1,
                'description': 'Estimated Medical Corpus at Retirement',
                'formula': 'Medical_FV = Current_Cover × (1 + i_med)^n',
                'calculation': f'Current Cover: Rs {medical_data.get("current_medical_cover", 0):,} | Inflation: {assumptions.get("medical_inflation", 10)}% | Years: {years_to_retirement}',
                'result': f'Rs {medical_data.get("medical_corpus_at_retirement", 0):,}'
            },
            {
                'step': 2,
                'description': 'Shortfall to be Funded',
                'formula': 'Shortfall = Medical_FV - (Current_Cover + Accumulated_Bonus)',
                'result': f'Rs {medical_data.get("balance_needed_at_retirement", 0):,}'
            }
        ]
    })

    # 4. Child Education Goal
    details.append({
        'section': 'Child Education Goal',
        'steps': [
            {
                'step': 1,
                'description': 'Inflation-Adjusted Cost of Education',
                'formula': 'FV = Current_Cost × (1 + i)^n',
                'calculation': f'Today: Rs {result.get("education_corpus_today", 0):,} | Inflation: {assumptions.get("inflation", 6)}% | Years: {assumptions.get("education_years", 0)}',
                'result': f'Rs {result.get("education_future_needed", 0):,}'
            },
            {
                'step': 2,
                'description': 'Net Corpus Needed (After existing investments)',
                'result': f'Rs {result.get("education_net_corpus", 0):,}'
            }
        ]
    })

    # 5. Child Marriage Goal
    details.append({
        'section': 'Child Marriage Goal',
        'steps': [
            {
                'step': 1,
                'description': 'Inflation-Adjusted Cost of Marriage',
                'formula': 'FV = Current_Cost × (1 + i)^n',
                'calculation': f'Today: Rs {result.get("marriage_corpus_today", 0):,} | Inflation: {assumptions.get("inflation", 6)}% | Years: {assumptions.get("marriage_years", 0)}',
                'result': f'Rs {result.get("marriage_future_needed", 0):,}'
            },
            {
                'step': 2,
                'description': 'Net Corpus Needed (After existing investments)',
                'result': f'Rs {result.get("marriage_net_corpus", 0):,}'
            }
        ]
    })

    # 6. Emergency Fund
    details.append({
        'section': 'Emergency Fund',
        'steps': [
            {
                'step': 1,
                'description': 'Total Fund Required (6 Months Expenses)',
                'formula': 'Fund = Monthly_Expense × 6',
                'calculation': f'Monthly: Rs {int(total_expenses/12):,} × 6',
                'result': f'Rs {result.get("emergency_fund_needed", 0):,}'
            },
            {
                'step': 2,
                'description': 'Current Shortfall',
                'result': f'Rs {result.get("emergency_fund_shortfall", 0):,}'
            }
        ]
    })

    # 7. Financial Health & Ratios
    details.append({
        'section': 'Financial Health & Ratios',
        'steps': [
            {
                'step': 1,
                'description': 'Savings Rate',
                'formula': 'Rate = (Income - Expense) / Income',
                'result': f'{result.get("savings_rate", 0)}%'
            },
            {
                'step': 2,
                'description': 'Overall Financial Health Score',
                'result': f'{result.get("financial_health_score", 0)}/100'
            }
        ]
    })

    # 8. Total Monthly Investment (Recommended Plan)
    details.append({
        'section': 'Recommended Monthly SIP Summary',
        'steps': [
            {
                'step': 1,
                'description': 'Aggregate Target Monthly Investment',
                'formula': 'Total_SIP = SIP_Retire + SIP_Medical + SIP_Edu + SIP_Marriage + SIP_Insurance + SIP_Emergency',
                'result': f'Rs {result.get("total_monthly_investment_income", 0):,}'
            }
        ]
    })

    return {
        "result_id": result.get("id"),
        "client_id": result.get("client_id"),
        "sections": details,
        "created_at": result.get("created_at")
    }


@router.get("/bridge/analysis/{id}/pdf")
async def download_analysis_pdf_bridge(
    id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Download Financial Analysis Report in PDF format."""
    result_data, profile_data = await fetch_analysis_data(id, bridge)
    if not profile_data:
        raise HTTPException(404, f"Financial profile not found for ID: {id} [DEBUG: PDF_V4]")
    
    if not result_data:
        raise HTTPException(400, "No calculation results found for this profile. Please click 'View Calculation' and run a recalculation first.")

    client = await bridge.get(f"/clients/{result_data.get('client_id')}")
    client_name = client.get("client_name", "Valued Client")

    # Fetch IA master data
    ia_logo_path = None
    ia_name = None
    try:
        ia_master = await bridge.get("/ia-master")
        if ia_master:
            ia_logo_path = ia_master.get("ia_logo_path")
            ia_name = ia_master.get("ia_name") or ia_master.get("entity_name")
    except:
        pass

    # Convert dicts to objects for the generator
    result_obj = dict_to_obj(result_data)
    profile_obj = dict_to_obj(profile_data)
    # Inject client object into profile_obj as generator expects profile.client.advisor_name
    profile_obj.client = dict_to_obj(client)

    pdf_buffer = FinancialReportGenerator.generate_pdf(
        result=result_obj,
        profile=profile_obj,
        client_name=client_name,
        ia_logo_path=ia_logo_path,
        ia_name=ia_name
    )

    filename = f"Financial_Analysis_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/bridge/analysis/{id}/word")
async def download_analysis_word_bridge(
    id: str,
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Download Financial Analysis Report in Word format."""
    result_data, profile_data = await fetch_analysis_data(id, bridge)
    if not profile_data:
        raise HTTPException(404, f"Financial profile not found for ID: {id} [DEBUG: WORD_V4]")
        
    if not result_data:
        raise HTTPException(400, "No calculation results found for this profile. Please click 'View Calculation' and run a recalculation first.")

    client = await bridge.get(f"/clients/{result_data.get('client_id')}")
    client_name = client.get("client_name", "Valued Client")

    # Fetch IA master data
    ia_logo_path = None
    ia_name = None
    try:
        ia_master = await bridge.get("/ia-master")
        if ia_master:
            ia_logo_path = ia_master.get("ia_logo_path")
            ia_name = ia_master.get("ia_name") or ia_master.get("entity_name")
    except:
        pass

    result_obj = dict_to_obj(result_data)
    profile_obj = dict_to_obj(profile_data)
    profile_obj.client = dict_to_obj(client)

    word_buffer = FinancialReportGenerator.generate_docx(
        result=result_obj,
        profile=profile_obj,
        client_name=client_name,
        ia_logo_path=ia_logo_path,
        ia_name=ia_name
    )

    filename = f"Financial_Analysis_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx"
    
    return StreamingResponse(
        word_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/bridge/form")
async def download_blank_form_bridge(
    bridge: BridgeClient = Depends(get_bridge_client),
):
    """Generate and download a blank Financial Analysis Form."""
    # Fetch IA metadata
    ia_logo_path = None
    ia_name = None
    try:
        ia_master = await bridge.get("/ia-master")
        if ia_master:
            ia_logo_path = ia_master.get("ia_logo_path")
            ia_name = ia_master.get("ia_name") or ia_master.get("entity_name")
    except:
        pass

    pdf_buffer = FinancialReportGenerator.generate_blank_form(ia_logo_path=ia_logo_path, ia_name=ia_name)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Financial_Analysis_Blank_Form.pdf"}
    )
