"""
Financial Analysis Service — Business Logic Layer.
Orchestrates calculations, AI commentary, audit logging, and report generation.
"""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.client import ClientProfile
from app.models.ia_master import IAMaster
from app.models.financial_analysis import FinancialAnalysisProfile, FinancialAnalysisResult
from app.schemas.financial_analysis_schema import FinancialAnalysisCreate
from app.analysis.financial_calculator import FinancialCalculator, safe_float
from app.analysis.ai_commentary import SystemCommentaryGenerator


class FinancialAnalysisService:

    @staticmethod
    def create_analysis(db: Session, analysis_in: FinancialAnalysisCreate) -> FinancialAnalysisResult:
        """
        Create a new financial analysis for a client.
        Steps: validate client → snapshot profile → calculate → generate system commentary → save → audit.
        """
        # 1. Validate client exists
        client = db.query(ClientProfile).filter(
            ClientProfile.id == analysis_in.client_id,
            ClientProfile.deleted_at == None
        ).first()
        if not client:
            raise ValueError("Client not found or has been deactivated.")

        # 2. Calculate client age
        client_age = FinancialCalculator.calculate_current_age(analysis_in.dob)
        if client_age is None:
            raise ValueError("Invalid date of birth. Client must be at least 18 years old.")

        # 3. Prepare financial inputs
        expenses_dict = analysis_in.expenses.model_dump()
        assets_dict = analysis_in.assets.model_dump()
        liabilities_dict = analysis_in.liabilities.model_dump()
        insurance_dict = analysis_in.insurance.model_dump()
        assumptions_dict = analysis_in.assumptions.model_dump()

        total_expenses = analysis_in.expenses.total
        total_assets = analysis_in.assets.total
        total_liabilities = analysis_in.liabilities.total
        net_worth = total_assets - total_liabilities

        # 4. Perform comprehensive analysis
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

        # 5. Perform separate HLV and Medical calculations for storage
        hlv_data = FinancialCalculator.perform_hlv_calculations(
            client_age=client_age,
            annual_income=analysis_in.annual_income,
            annual_expenses=total_expenses,
            net_worth=net_worth,
            current_life_cover=insurance_dict.get('life_cover', 0),
            total_assets=total_assets,
            current_liabilities=total_liabilities,
            assumptions=assumptions_dict,
            spouse_life_expectancy=assumptions_dict.get('le_spouse', 0),
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

        # 6. Generate system commentary (unless excluded)
        ai_analysis = None
        if not analysis_in.exclude_ai:
            ai_analysis = SystemCommentaryGenerator.generate_all_commentary(
                calculations=calculations,
                hlv_data=hlv_data,
                medical_data=medical_data,
                client_name=client.client_name,
            )

        # 7. Extract cash flow from calculations
        cash_flow = calculations.pop('cash_flow_analysis', None)

        # 8. Save profile snapshot
        children_list = [c.model_dump() for c in analysis_in.children]
        # Convert date objects in children to strings for JSON serialization
        for child in children_list:
            if child.get('dob') and hasattr(child['dob'], 'isoformat'):
                child['dob'] = child['dob'].isoformat()

        profile = FinancialAnalysisProfile(
            client_id=analysis_in.client_id,
            pan=analysis_in.pan,
            contact=analysis_in.contact,
            email=analysis_in.email,
            occupation=analysis_in.occupation,
            dob=analysis_in.dob,
            annual_income=analysis_in.annual_income,
            spouse_name=analysis_in.spouse_name,
            spouse_dob=analysis_in.spouse_dob,
            spouse_occupation=analysis_in.spouse_occupation,
            children=children_list,
            expenses=expenses_dict,
            assets=assets_dict,
            liabilities=liabilities_dict,
            insurance=insurance_dict,
            assumptions=assumptions_dict,
            medical_bonus_years=analysis_in.medical_bonus_years,
            medical_bonus_percentage=analysis_in.medical_bonus_percentage,
            education_investment_pct=analysis_in.education_investment_pct,
            marriage_investment_pct=analysis_in.marriage_investment_pct,
            exclude_ai=analysis_in.exclude_ai,
            disclaimer_text=analysis_in.disclaimer_text,
            discussion_notes=analysis_in.discussion_notes,
            record_version_control_statement=analysis_in.record_version_control_statement,
        )
        db.add(profile)
        db.flush()  # Get profile.id before creating result

        # 9. Save analysis result
        result = FinancialAnalysisResult(
            profile_id=profile.id,
            client_id=analysis_in.client_id,
            calculations=calculations,
            hlv_data=hlv_data,
            medical_data=medical_data,
            cash_flow_analysis=cash_flow,
            ai_analysis=ai_analysis,
            financial_health_score=calculations.get('financial_health_score', 0),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        return result

    @staticmethod
    def get_analysis(db: Session, result_id: uuid.UUID) -> Optional[FinancialAnalysisResult]:
        """Get a specific analysis result by ID."""
        return db.query(FinancialAnalysisResult).filter(
            FinancialAnalysisResult.id == result_id
        ).first()

    @staticmethod
    def get_analysis_by_client(db: Session, client_id: uuid.UUID) -> Optional[FinancialAnalysisResult]:
        """Get the latest analysis result for a client."""
        return db.query(FinancialAnalysisResult).filter(
            FinancialAnalysisResult.client_id == client_id
        ).order_by(FinancialAnalysisResult.created_at.desc()).first()

    @staticmethod
    def list_analyses(db: Session, client_id: Optional[uuid.UUID] = None) -> List[dict]:
        """List all analysis results, optionally filtered by client_id."""
        query = db.query(
            FinancialAnalysisResult.id,
            FinancialAnalysisResult.client_id,
            FinancialAnalysisResult.financial_health_score,
            FinancialAnalysisResult.created_at,
            FinancialAnalysisResult.calculations,
            FinancialAnalysisResult.hlv_data,
            ClientProfile.client_name,
        ).join(
            ClientProfile, FinancialAnalysisResult.client_id == ClientProfile.id
        )

        if client_id:
            query = query.filter(FinancialAnalysisResult.client_id == client_id)

        results = query.order_by(FinancialAnalysisResult.created_at.desc()).all()

        return [
            {
                'id': r.id,
                'client_id': r.client_id,
                'client_name': r.client_name,
                'calculations': r.calculations,
                'hlv_data': r.hlv_data,
                'financial_health_score': r.financial_health_score,
                'created_at': r.created_at,
            }
            for r in results
        ]

    @staticmethod
    def get_calculation_details(db: Session, result_id: uuid.UUID) -> Optional[dict]:
        """Generate step-by-step calculation breakdown."""
        result = FinancialAnalysisService.get_analysis(db, result_id)
        if not result:
            return None

        profile = db.query(FinancialAnalysisProfile).filter(
            FinancialAnalysisProfile.id == result.profile_id
        ).first()
        if not profile:
            return None

        calculations = result.calculations
        hlv_data = result.hlv_data
        assumptions = profile.assumptions
        total_expenses = calculations.get('total_expenses', 0)
        client_age = calculations.get('client_age', 0)
        insurance = profile.insurance

        # Build step-by-step details (same structure as get_calculation_details in finplan.py)
        details = []

        # 1. HLV
        details.append({
            'section': 'Human Life Value (HLV) Calculation',
            'steps': [
                {
                    'step': 1,
                    'description': 'Income Replacement Method Calculation',
                    'formula': f'HLV = Annual Income × SOL% × PV of annuity for {calculations.get("years_considered_income", 0)} years at {assumptions.get("pre_ret_rate", 12)}% return rate',
                    'calculation': f'Annual Income: Rs {int(profile.annual_income):,} × {assumptions.get("sol_hlv", 70)}% = Rs {int(profile.annual_income * assumptions.get("sol_hlv", 70) / 100):,} (annual replaceable income)',
                    'result': f'Gross HLV (Income Method): Rs {calculations.get("hlv_income_method", 0):,}',
                },
                {
                    'step': 2,
                    'description': 'Expense Replacement Method Calculation',
                    'formula': f'HLV = Annual Expenses × SOL% × ({assumptions.get("le_spouse", 85)} - {client_age}) years inflation-adjusted',
                    'calculation': f'Annual Expenses: Rs {int(total_expenses):,} × {assumptions.get("sol_hlv", 70)}% = Rs {int(total_expenses * assumptions.get("sol_hlv", 70) / 100):,} (annual replaceable expenses)',
                    'result': f'Gross HLV (Expense Method): Rs {calculations.get("hlv_expense_method", 0):,}',
                },
                {
                    'step': 3,
                    'description': 'Net HLV Calculation',
                    'formula': 'Net HLV = Gross HLV - Existing Financial Assets + Current Liabilities - Current Life Cover',
                    'calculation': f'Gross HLV (Income): Rs {hlv_data.get("hlv_income_method", 0):,}\n- Existing Financial Assets: Rs {hlv_data.get("existing_financial_assets", 0):,}\n+ Current Liabilities: Rs {hlv_data.get("current_liabilities", 0):,}\n- Current Life Cover: Rs {hlv_data.get("current_life_cover", 0):,}',
                    'result': f'Net HLV (Income Method): Rs {hlv_data.get("net_hlv_income", 0):,}',
                },
            ],
        })

        # 2. Medical
        details.append({
            'section': 'Medical Coverage Analysis',
            'steps': [
                {
                    'step': 1,
                    'description': 'Future Medical Corpus Required at Retirement',
                    'formula': 'Medical Corpus at Retirement = Current Cover × (1 + Medical Inflation)^{years_to_retirement}',
                    'calculation': f'Current Cover: Rs {insurance.get("med_cover", 0):,}\nMedical Inflation: {assumptions.get("medical_inflation", 10)}%\nYears to Retirement: {calculations.get("years_to_retirement", 0)} years',
                    'result': f'Required at Retirement: Rs {calculations.get("medical_corpus_at_retirement", 0):,}',
                },
                {
                    'step': 2,
                    'description': 'Balance Needed Calculation',
                    'formula': 'Balance Needed = Required Corpus - Total Coverage',
                    'calculation': f'Required Corpus: Rs {calculations.get("medical_corpus_at_retirement", 0):,}\n- Total Coverage: Rs {calculations.get("total_coverage_at_retirement", 0):,}',
                    'result': f'Balance Needed: Rs {calculations.get("balance_needed_at_retirement", 0):,}',
                },
            ],
        })

        # 3. Retirement
        years_to_retirement = max(0, int(assumptions.get('retirement_age', 60)) - client_age)
        years_in_retirement = max(0, int(assumptions.get('le_client', 85)) - int(assumptions.get('retirement_age', 60)))
        e_adjusted = profile.annual_income * (assumptions.get('sol_ret', 80) / 100) # Wait, should be annual_expenses?
        # Re-check: e_adjusted = E_current * SOL. My code uses annual_expenses.
        e_adjusted = total_expenses * (assumptions.get('sol_ret', 80) / 100)
        e_retirement = e_adjusted * ((1 + assumptions.get('inflation', 6)/100) ** years_to_retirement)

        details.append({
            'section': 'Retirement Corpus Calculation (Rigorous Model)',
            'steps': [
                {
                    'step': 1,
                    'description': 'Adjust Expense for Lifestyle',
                    'formula': 'E_adjusted = Current Annual Expense × SOL Factor',
                    'calculation': f'Rs {int(total_expenses):,} × {assumptions.get("sol_ret", 80)}% = Rs {int(e_adjusted):,}',
                    'result': f'Adjusted Expense: Rs {int(e_adjusted):,}',
                },
                {
                    'step': 2,
                    'description': 'Inflate Expense to Retirement Date',
                    'formula': 'E_retirement = E_adjusted × (1 + i)^t',
                    'calculation': f'Rs {int(e_adjusted):,} × (1 + {assumptions.get("inflation", 6)}%)^{years_to_retirement} years',
                    'result': f'First-year retirement expense: Rs {int(e_retirement):,}',
                },
                {
                    'step': 3,
                    'description': 'Compute Retirement Corpus Needed',
                    'formula': 'Corpus = E_retirement × [1 - ((1 + i) / (1 + r))^n] / (r - i)',
                    'calculation': f'E_retirement: Rs {int(e_retirement):,}\nInflation (i): {assumptions.get("inflation", 6)}%\nReturn (r): {assumptions.get("post_ret_rate", 8)}%\nDuration (n): {years_in_retirement} years',
                    'result': f'Total Corpus Required: Rs {calculations.get("retirement_corpus_at_retirement", 0):,}',
                },
                {
                    'step': 4,
                    'description': 'Monthly Investment Required',
                    'formula': 'Monthly = Net Corpus / FV Annuity Factor',
                    'calculation': f'Target: Rs {calculations.get("net_retirement_corpus_needed", 0):,}\nMonths: {years_to_retirement * 12}',
                    'result': f'Required Monthly SIP: Rs {calculations.get("monthly_investment_retirement", 0):,}',
                },
            ],
        })

        # 4. Child Goals
        details.append({
            'section': 'Child Goals Calculation',
            'steps': [
                {
                    'step': 1,
                    'description': 'Future Value of Education Goal',
                    'formula': 'FV = Current Cost × (1 + Inflation)^years',
                    'calculation': f'Current Cost: Rs {calculations.get("education_corpus_today", 0):,} | Inflation: {assumptions.get("inflation", 6)}% | Years: {assumptions.get("education_years", 5)}',
                    'result': f'Future Education Cost: Rs {calculations.get("education_future_needed", 0):,}',
                },
                {
                    'step': 2,
                    'description': 'Net Corpus Needed (After existing investments)',
                    'formula': 'Net_Corpus = Future_Cost - FV_Allocated_Investments',
                    'calculation': f'Future Cost: Rs {calculations.get("education_future_needed", 0):,} - FV Investments: Rs {calculations.get("fv_allocated_education", 0):,}',
                    'result': f'Net Requirement: Rs {calculations.get("education_net_corpus", 0):,}',
                },
                {
                    'step': 3,
                    'description': 'Monthly Investment for Education',
                    'formula': 'PMT = Net Requirement / FV annuity factor',
                    'calculation': f'Net Requirement: Rs {calculations.get("education_net_corpus", 0):,} | Term: {assumptions.get("education_years", 5) * 12} months',
                    'result': f'Monthly Investment: Rs {calculations.get("monthly_investment_education", 0):,}',
                },
            ],
        })

        # 5. Emergency Fund
        details.append({
            'section': 'Emergency Fund Analysis',
            'steps': [
                {
                    'step': 1,
                    'description': 'Emergency Fund Required',
                    'formula': 'Emergency Fund = Monthly Expenses × 6 months',
                    'calculation': f'Monthly Expenses: Rs {int(total_expenses / 12):,} × 6 months coverage',
                    'result': f'Emergency Fund Required: Rs {calculations.get("emergency_fund_needed", 0):,}',
                },
                {
                    'step': 2,
                    'description': 'Emergency Fund Shortfall',
                    'formula': 'Shortfall = Required - Current Cash at Bank',
                    'calculation': f'Required: Rs {calculations.get("emergency_fund_needed", 0):,} - Available Cash: Rs {max(0, calculations.get("emergency_fund_needed", 0) - calculations.get("emergency_fund_shortfall", 0)):,}',
                    'result': f'Shortfall: Rs {calculations.get("emergency_fund_shortfall", 0):,}',
                },
            ],
        })

        return {
            'result_id': result.id,
            'client_id': result.client_id,
            'sections': details,
            'created_at': result.created_at,
        }
