"""
Financial Calculator — Core Analysis Engine
Extracted from finplan.py (standalone Flask app).
Pure Python, no framework dependency.
Contains all financial planning formulas: HLV, Medical, Retirement, Child Goals,
Emergency Fund, Cash Flow Analysis, and Financial Health Score.
"""
from datetime import datetime, date
from typing import Optional


def safe_float(value, default=0.0):
    """Safely convert a value to float, handling empty strings and negative values."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    if isinstance(value, str):
        value = value.strip().replace(',', '')
        if value == '':
            return default
        try:
            float_val = float(value)
            return max(0.0, float_val)
        except ValueError:
            return default
    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        return default


class FinancialCalculator:
    """
    Core financial calculation engine.
    All methods are static — no state, no DB access, pure math.
    """

    # ──────────────────────────────────────────────
    # Age Helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def calculate_current_age(dob_input) -> Optional[int]:
        """
        Calculate current age from date of birth.
        Accepts: date object, or string in 'dd-mm-yyyy' or 'yyyy-mm-dd' format.
        Returns None if age < 18 or input is invalid.
        """
        try:
            if isinstance(dob_input, date):
                dob = dob_input
            elif isinstance(dob_input, str):
                dob_str = dob_input.strip()
                # Try dd-mm-yyyy first (original Flask format)
                try:
                    dob = datetime.strptime(dob_str, "%d-%m-%Y").date()
                except ValueError:
                    # Try yyyy-mm-dd (database format)
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            else:
                return None

            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                return None
            return age
        except Exception:
            return None

    @staticmethod
    def calculate_child_age(child_dob_input) -> Optional[int]:
        """Calculate child's age from dob (date object or string)."""
        try:
            if not child_dob_input:
                return None
            if isinstance(child_dob_input, date):
                dob = child_dob_input
            elif isinstance(child_dob_input, str):
                dob_str = child_dob_input.strip()
                try:
                    dob = datetime.strptime(dob_str, "%d-%m-%Y").date()
                except ValueError:
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            else:
                return None

            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # Core Financial Math
    # ──────────────────────────────────────────────

    @staticmethod
    def calculate_future_value(pv, rate, years):
        """Calculate future value with compound interest."""
        if rate == 0:
            return pv
        return pv * ((1 + rate / 100) ** years)

    @staticmethod
    def calculate_present_value(fv, rate, years):
        """Calculate present value."""
        if rate == 0:
            return fv
        return fv / ((1 + rate / 100) ** years)

    @staticmethod
    def calculate_annuity_pv(pmt, rate, years):
        """Calculate present value of annuity."""
        if rate == 0:
            return pmt * years
        return pmt * ((1 - (1 + rate / 100) ** -years) / (rate / 100))

    @staticmethod
    def calculate_inflation_adjusted_corpus(current_corpus, years, inflation_rate):
        """Calculate future value of corpus with inflation."""
        if years <= 0:
            return current_corpus
        return current_corpus * ((1 + inflation_rate / 100) ** years)

    # ──────────────────────────────────────────────
    # HLV — Human Life Value
    # ──────────────────────────────────────────────

    @staticmethod
    def calculate_hlv_income_method(income, retirement_age, current_age, sol_percent, return_rate):
        """Calculate Human Life Value using income replacement method."""
        working_years = int(retirement_age) - int(current_age)
        if working_years <= 0:
            return 0
        future_income = income * (sol_percent / 100)
        pv = FinancialCalculator.calculate_annuity_pv(future_income, return_rate, working_years)
        return int(max(1, pv))

    @staticmethod
    def calculate_hlv_expense_method(expenses, spouse_life_expectancy, current_age, sol_percent, inflation):
        """Calculate Human Life Value using expense replacement method."""
        remaining_years = int(spouse_life_expectancy) - int(current_age)
        if remaining_years <= 0:
            return 0
        total_future_expenses = 0
        for year in range(1, remaining_years + 1):
            future_expenses = expenses * (sol_percent / 100) * ((1 + inflation / 100) ** year)
            total_future_expenses += future_expenses
        return int(max(1, total_future_expenses))

    @staticmethod
    def perform_hlv_calculations(**kwargs) -> dict:
        """Perform complete HLV calculations with guaranteed non-zero results."""
        client_age = int(kwargs.get('client_age', 0))
        annual_income = kwargs.get('annual_income', 0)
        annual_expenses = kwargs.get('annual_expenses', 0)
        current_life_cover = kwargs.get('current_life_cover', 0)
        total_assets = kwargs.get('total_assets', 0)
        current_liabilities = kwargs.get('current_liabilities', 0)
        assumptions = kwargs.get('assumptions', {})
        allocated_investment_education = kwargs.get('allocated_investment_education', 0)
        allocated_investment_marriage = kwargs.get('allocated_investment_marriage', 0)
        land_building_value = kwargs.get('land_building_value', 0)
        spouse_life_expectancy = int(kwargs.get('spouse_life_expectancy', assumptions.get('le_spouse', 85)))

        # HLV Income Method
        hlv_income = FinancialCalculator.calculate_hlv_income_method(
            annual_income, assumptions.get('retirement_age', 60), client_age,
            assumptions.get('sol_hlv', 70), assumptions.get('pre_ret_rate', 12))

        years_considered_income = max(0, int(assumptions.get('retirement_age', 60)) - client_age)

        # HLV Expense Method
        hlv_expense = FinancialCalculator.calculate_hlv_expense_method(
            annual_expenses, spouse_life_expectancy, client_age,
            assumptions.get('sol_hlv', 70), assumptions.get('inflation', 6))

        years_considered_expense = max(0, spouse_life_expectancy - client_age)

        # Existing financial assets (Total Assets - Land - Allocated investments)
        existing_financial_assets = max(
            0, total_assets - land_building_value - allocated_investment_education - allocated_investment_marriage)

        # Net HLV = max(0, Gross HLV - Existing Assets + Liabilities - Life Cover)
        additional_cover_income = max(
            0, hlv_income - existing_financial_assets + current_liabilities - current_life_cover)
        additional_cover_expense = max(
            0, hlv_expense - existing_financial_assets + current_liabilities - current_life_cover)

        net_hlv_income = additional_cover_income
        net_hlv_expense = additional_cover_expense

        # Monthly investment for HLV cover
        years_to_retirement = max(0, int(assumptions.get('retirement_age', 60)) - client_age)
        monthly_investment_insurance_income = 0
        monthly_investment_insurance_expense = 0
        if years_to_retirement > 0:
            if additional_cover_income > 0:
                monthly_investment_insurance_income = int(additional_cover_income / (years_to_retirement * 12))
            if additional_cover_expense > 0:
                monthly_investment_insurance_expense = int(additional_cover_expense / (years_to_retirement * 12))

        # Ensure non-zero for display
        if hlv_income == 0 and annual_income > 0:
            hlv_income = max(1, int(annual_income * 10))
        if hlv_expense == 0 and annual_expenses > 0:
            hlv_expense = max(1, int(annual_expenses * 10))

        return {
            'hlv_income_method': int(hlv_income),
            'hlv_expense_method': int(hlv_expense),
            'years_considered_income': int(years_considered_income),
            'years_considered_expense': int(years_considered_expense),
            'spouse_life_expectancy_used': int(spouse_life_expectancy),
            'net_hlv_income': int(net_hlv_income),
            'net_hlv_expense': int(net_hlv_expense),
            'additional_life_cover_needed_income': int(additional_cover_income),
            'additional_life_cover_needed_expense': int(additional_cover_expense),
            'monthly_investment_insurance_income': int(monthly_investment_insurance_income),
            'monthly_investment_insurance_expense': int(monthly_investment_insurance_expense),
            'existing_financial_assets': int(existing_financial_assets),
            'current_liabilities': int(current_liabilities),
            'current_life_cover': int(current_life_cover),
            'land_building_value': int(land_building_value),
            'allocated_investment_education': int(allocated_investment_education),
            'allocated_investment_marriage': int(allocated_investment_marriage),
            'hlv_calculation_formula': 'NET HLV = max(0, Gross HLV - Existing Financial Assets + Current Liabilities - Current Life Insurance Cover)',
            'income_method_explanation': f'Income Replacement Method: {years_considered_income} years (Retirement Age {assumptions.get("retirement_age", 60)} - Current Age {client_age})',
            'expense_method_explanation': f'Expense Replacement Method: {years_considered_expense} years (Spouse Life Expectancy {spouse_life_expectancy} - Current Age {client_age})',
        }

    # ──────────────────────────────────────────────
    # Medical Corpus
    # ──────────────────────────────────────────────

    @staticmethod
    def calculate_medical_corpus_requirements(current_medical_cover, current_age,
                                               retirement_age, life_expectancy,
                                               medical_inflation,
                                               medical_bonus_years=0,
                                               medical_bonus_percentage=0):
        """Calculate medical corpus requirements at retirement and life expectancy."""
        years_to_retirement = int(retirement_age) - int(current_age)
        years_to_life_expectancy = int(life_expectancy) - int(current_age)

        if years_to_retirement <= 0 or years_to_life_expectancy <= 0:
            return 0, 0, 0, 0, 0, 0, 0

        # Future value of medical cover at each milestone
        medical_corpus_at_retirement = current_medical_cover * ((1 + medical_inflation / 100) ** years_to_retirement)
        medical_corpus_at_life_expectancy = current_medical_cover * ((1 + medical_inflation / 100) ** years_to_life_expectancy)

        # Coverage accumulation with bonus
        total_coverage_at_retirement = current_medical_cover
        total_coverage_at_life_expectancy = current_medical_cover

        if medical_bonus_years > 0 and medical_bonus_percentage > 0:
            total_bonus_cover = 0
            for year in range(1, min(int(medical_bonus_years), years_to_retirement) + 1):
                bonus_cover = current_medical_cover * (medical_bonus_percentage / 100)
                total_bonus_cover += bonus_cover

            total_coverage_at_retirement = current_medical_cover + total_bonus_cover
            total_coverage_at_life_expectancy = total_coverage_at_retirement  # No growth after bonus

        # Balance needed (shortfall)
        balance_needed_at_retirement = max(0, medical_corpus_at_retirement - total_coverage_at_retirement)
        balance_needed_at_life_expectancy = max(0, medical_corpus_at_life_expectancy - total_coverage_at_life_expectancy)

        return (
            0,  # medical_corpus_today — removed per requirements
            int(medical_corpus_at_retirement),
            int(medical_corpus_at_life_expectancy),
            int(total_coverage_at_retirement),
            int(total_coverage_at_life_expectancy),
            int(balance_needed_at_retirement),
            int(balance_needed_at_life_expectancy),
        )

    @staticmethod
    def perform_medical_calculations(**kwargs) -> dict:
        """Perform complete medical corpus calculations."""
        client_age = int(kwargs.get('client_age', 0))
        current_medical_cover = kwargs.get('current_medical_cover', 0)
        assumptions = kwargs.get('assumptions', {})
        medical_bonus_years = kwargs.get('medical_bonus_years', 0)
        medical_bonus_percentage = kwargs.get('medical_bonus_percentage', 0)

        (
            medical_corpus_today,
            medical_corpus_at_retirement,
            medical_corpus_at_life_expectancy,
            total_coverage_at_retirement,
            total_coverage_at_life_expectancy,
            balance_needed_at_retirement,
            balance_needed_at_life_expectancy,
        ) = FinancialCalculator.calculate_medical_corpus_requirements(
            current_medical_cover, client_age,
            int(assumptions.get('retirement_age', 60)),
            int(assumptions.get('le_client', 85)),
            assumptions.get('medical_inflation', 10),
            medical_bonus_years, medical_bonus_percentage)

        # Monthly investment for medical shortfall
        years_to_retirement = max(0, int(assumptions.get('retirement_age', 60)) - client_age)
        monthly_investment_medical_retirement = 0
        if years_to_retirement > 0 and balance_needed_at_retirement > 0:
            monthly_investment_medical_retirement = int(balance_needed_at_retirement / (years_to_retirement * 12))

        years_to_life_expectancy = max(0, int(assumptions.get('le_client', 85)) - client_age)
        monthly_investment_medical_life_expectancy = 0
        if years_to_life_expectancy > 0 and balance_needed_at_life_expectancy > 0:
            monthly_investment_medical_life_expectancy = int(
                balance_needed_at_life_expectancy / (years_to_life_expectancy * 12))

        return {
            'medical_corpus_today': int(medical_corpus_today),
            'medical_corpus_at_retirement': int(medical_corpus_at_retirement),
            'medical_corpus_at_life_expectancy': int(medical_corpus_at_life_expectancy),
            'total_coverage_at_retirement': int(total_coverage_at_retirement),
            'total_coverage_at_life_expectancy': int(total_coverage_at_life_expectancy),
            'balance_needed_at_retirement': int(balance_needed_at_retirement),
            'balance_needed_at_life_expectancy': int(balance_needed_at_life_expectancy),
            'monthly_investment_medical_retirement': int(monthly_investment_medical_retirement),
            'monthly_investment_medical_life_expectancy': int(monthly_investment_medical_life_expectancy),
            'current_medical_cover': int(current_medical_cover),
            'medical_bonus_years': int(medical_bonus_years),
            'medical_bonus_percentage': float(medical_bonus_percentage),
        }

    # ──────────────────────────────────────────────
    # Retirement Corpus & Cash Flow
    # ──────────────────────────────────────────────

    @staticmethod
    def calculate_retirement_corpus_at_retirement(annual_expenses, retirement_age, current_age,
                                                   life_expectancy, sol_percent, inflation, post_ret_rate):
        """Calculate retirement corpus needed AT RETIREMENT AGE (Future Value) using rigorous inflation-adjusted model."""
        years_to_retirement = max(0, int(retirement_age) - int(current_age))
        years_in_retirement = max(0, int(life_expectancy) - int(retirement_age))
        
        if years_in_retirement <= 0:
            return 0

        # Step 2: Adjust Expense for Lifestyle
        e_adjusted = annual_expenses * (sol_percent / 100)
        
        # Step 3: Inflate Expense to Retirement
        i_rate = inflation / 100
        e_retirement = e_adjusted * ((1 + i_rate) ** years_to_retirement)
        
        # Steps 4 & 5: Compute Factor and Corpus
        r_rate = post_ret_rate / 100
        
        if abs(r_rate - i_rate) < 0.0001:
            # If r == i, PV of growing annuity is n * W1 / (1 + r)
            corpus_at_retirement = years_in_retirement * e_retirement / (1 + r_rate)
        else:
            # Factor = [1 - ((1 + i) / (1 + r))^n] / (r - i)
            factor = (1 - ((1 + i_rate) / (1 + r_rate)) ** years_in_retirement) / (r_rate - i_rate)
            corpus_at_retirement = e_retirement * factor

        return int(max(0, corpus_at_retirement))

    @staticmethod
    def calculate_cash_flow_analysis(corpus_at_retirement, annual_expenses, retirement_age,
                                     current_age, life_expectancy, sol_percent, inflation, post_ret_rate):
        """Generate year-by-year cash flow analysis with automated depletion at life expectancy."""
        years_to_retirement = max(0, int(retirement_age) - int(current_age))
        years_in_retirement = max(0, int(life_expectancy) - int(retirement_age))
        
        if years_in_retirement <= 0 or corpus_at_retirement <= 0:
            return []

        # First year withdrawal is E_adjusted inflated for years_to_retirement
        e_adjusted = annual_expenses * (sol_percent / 100)
        i_rate = inflation / 100
        first_year_withdrawal = e_adjusted * ((1 + i_rate) ** years_to_retirement)
        
        balance = corpus_at_retirement
        cash_flow = []

        for year in range(1, years_in_retirement + 1):
            opening_balance = balance
            growth = balance * (post_ret_rate / 100)
            
            # Withdrawal increases by inflation each year
            withdrawal = first_year_withdrawal * ((1 + i_rate) ** (year - 1))

            # Final year correction to match zero balance (Step 5/6 requirement)
            if year == years_in_retirement:
                withdrawal = opening_balance + growth
                closing_balance = 0
            else:
                closing_balance = opening_balance + growth - withdrawal
                # Ensure no negative balance in simulation
                if closing_balance < 0:
                    withdrawal = opening_balance + growth
                    closing_balance = 0

            cash_flow.append({
                'year': year,
                'retirement_age_year': int(retirement_age) + year - 1,
                'opening_balance': int(opening_balance),
                'investment_growth': int(growth),
                'annual_withdrawal': int(withdrawal),
                'closing_balance': int(closing_balance),
                'age_at_year_end': int(retirement_age) + year,
            })
            balance = closing_balance
            if balance <= 0 and year < years_in_retirement:
                # If balance hits zero early, continue with zeros
                pass

        return cash_flow

    # ──────────────────────────────────────────────
    # Comprehensive Analysis (Orchestrator)
    # ──────────────────────────────────────────────

    @staticmethod
    def perform_comprehensive_analysis(**kwargs) -> dict:
        """
        Perform full financial analysis.
        This is the main entry point that combines HLV, Medical, Retirement,
        Child Goals, Emergency Fund, and Financial Health Score.
        """
        client_age = int(kwargs.get('client_age', 0))
        annual_income = kwargs.get('annual_income', 0)
        annual_expenses = kwargs.get('annual_expenses', 0)
        net_worth = kwargs.get('net_worth', 0)
        current_life_cover = kwargs.get('current_life_cover', 0)
        current_medical_cover = kwargs.get('current_medical_cover', 0)
        existing_retirement_savings = kwargs.get('existing_retirement_savings', 0)
        total_assets = kwargs.get('total_assets', 0)
        current_liabilities = kwargs.get('current_liabilities', 0)
        assumptions = kwargs.get('assumptions', {})
        land_building_value = kwargs.get('land_building_value', 0)
        investments_value = kwargs.get('investments_value', 0)
        medical_bonus_years = kwargs.get('medical_bonus_years', 0)
        medical_bonus_percentage = kwargs.get('medical_bonus_percentage', 0)
        education_investment_pct = safe_float(kwargs.get('education_investment_pct', 0))
        marriage_investment_pct = safe_float(kwargs.get('marriage_investment_pct', 0))

        # ── 1. RETIREMENT ──
        retirement_corpus_at_retirement = FinancialCalculator.calculate_retirement_corpus_at_retirement(
            annual_expenses, int(assumptions.get('retirement_age', 60)), client_age,
            int(assumptions.get('le_client', 85)), assumptions.get('sol_ret', 80),
            assumptions.get('inflation', 6), assumptions.get('post_ret_rate', 8))

        years_to_retirement = max(0, int(assumptions.get('retirement_age', 60)) - client_age)

        future_value_existing_savings = FinancialCalculator.calculate_future_value(
            existing_retirement_savings, assumptions.get('pre_ret_rate', 12), years_to_retirement)

        net_retirement_corpus_needed = max(0, retirement_corpus_at_retirement - future_value_existing_savings)

        # Monthly investment for retirement
        monthly_investment_retirement = 0
        if years_to_retirement > 0 and net_retirement_corpus_needed > 0:
            rate = assumptions.get('pre_ret_rate', 12) / 12 / 100
            months = years_to_retirement * 12
            if rate > 0:
                fv_factor = ((1 + rate) ** months - 1) / rate
                monthly_investment_retirement = int(net_retirement_corpus_needed / fv_factor)
            else:
                monthly_investment_retirement = int(net_retirement_corpus_needed / months)

        # Cash flow analysis
        cash_flow = FinancialCalculator.calculate_cash_flow_analysis(
            retirement_corpus_at_retirement, annual_expenses,
            int(assumptions.get('retirement_age', 60)), client_age,
            int(assumptions.get('le_client', 85)), assumptions.get('sol_ret', 80),
            assumptions.get('inflation', 6), assumptions.get('post_ret_rate', 8))

        # ── 2. CHILD GOALS ──
        education_years = int(assumptions.get('education_years', 5))
        marriage_years = int(assumptions.get('marriage_years', 10))
        pre_ret_rate = assumptions.get('pre_ret_rate', 12)
        inflation = assumptions.get('inflation', 6)

        allocated_investment_education = investments_value * (education_investment_pct / 100)
        allocated_investment_marriage = investments_value * (marriage_investment_pct / 100)

        fv_factor_education = FinancialCalculator.calculate_future_value(1, pre_ret_rate, education_years) / 12 if education_years > 0 else 0
        fv_factor_marriage = FinancialCalculator.calculate_future_value(1, pre_ret_rate, marriage_years) / 12 if marriage_years > 0 else 0

        fv_allocated_education = allocated_investment_education * fv_factor_education if fv_factor_education > 0 else 0
        fv_allocated_marriage = allocated_investment_marriage * fv_factor_marriage if fv_factor_marriage > 0 else 0

        # Education
        child_education_corpus = assumptions.get('child_education_corpus', 0)
        if education_years > 0 and child_education_corpus > 0:
            education_future_needed = child_education_corpus * ((1 + inflation / 100) ** education_years)
            net_education_corpus = max(0, education_future_needed - fv_allocated_education)
            monthly_investment_education = 0
            if education_years > 0 and net_education_corpus > 0:
                rate_per_month = pre_ret_rate / 12 / 100
                months = education_years * 12
                if rate_per_month > 0:
                    fv_f = ((1 + rate_per_month) ** months - 1) / rate_per_month
                    monthly_investment_education = int(net_education_corpus / fv_f)
                else:
                    monthly_investment_education = int(net_education_corpus / months)
        else:
            education_future_needed = 0
            net_education_corpus = 0
            monthly_investment_education = 0

        # Marriage
        child_marriage_corpus = assumptions.get('child_marriage_corpus', 0)
        if marriage_years > 0 and child_marriage_corpus > 0:
            marriage_future_needed = child_marriage_corpus * ((1 + inflation / 100) ** marriage_years)
            net_marriage_corpus = max(0, marriage_future_needed - fv_allocated_marriage)
            monthly_investment_marriage = 0
            if marriage_years > 0 and net_marriage_corpus > 0:
                rate_per_month = pre_ret_rate / 12 / 100
                months = marriage_years * 12
                if rate_per_month > 0:
                    fv_f = ((1 + rate_per_month) ** months - 1) / rate_per_month
                    monthly_investment_marriage = int(net_marriage_corpus / fv_f)
                else:
                    monthly_investment_marriage = int(net_marriage_corpus / months)
        else:
            marriage_future_needed = 0
            net_marriage_corpus = 0
            monthly_investment_marriage = 0

        # ── 3. HLV ──
        hlv_results = FinancialCalculator.perform_hlv_calculations(
            client_age=client_age, annual_income=annual_income,
            annual_expenses=annual_expenses, net_worth=net_worth,
            current_life_cover=current_life_cover, total_assets=total_assets,
            current_liabilities=current_liabilities, assumptions=assumptions,
            spouse_life_expectancy=assumptions.get('le_spouse', 85),
            land_building_value=land_building_value,
            allocated_investment_education=allocated_investment_education,
            allocated_investment_marriage=allocated_investment_marriage)

        # ── 4. MEDICAL ──
        medical_results = FinancialCalculator.perform_medical_calculations(
            client_age=client_age, current_medical_cover=current_medical_cover,
            assumptions=assumptions, medical_bonus_years=medical_bonus_years,
            medical_bonus_percentage=medical_bonus_percentage)

        # ── 5. OTHER ──
        savings_rate = int(((annual_income - annual_expenses) / annual_income) * 100) if annual_income > 0 else 0

        # ── 6. EMERGENCY FUND ──
        emergency_fund_months = 6
        emergency_fund_needed = int((annual_expenses / 12) * emergency_fund_months)
        emergency_fund_shortfall = max(0, emergency_fund_needed - kwargs.get('cash_at_bank', 0))
        monthly_investment_emergency = int(emergency_fund_shortfall / 12)

        # ── 7. RETIREMENT READINESS ──
        retirement_readiness = 0
        if retirement_corpus_at_retirement > 0:
            retirement_readiness = int(min(100, (future_value_existing_savings / retirement_corpus_at_retirement) * 100))

        # ── 8. TOTAL MONTHLY INVESTMENT ──
        total_monthly_investment_income = (
            monthly_investment_retirement +
            medical_results.get('monthly_investment_medical_retirement', 0) +
            monthly_investment_education + monthly_investment_marriage +
            hlv_results.get('monthly_investment_insurance_income', 0) +
            monthly_investment_emergency)

        total_monthly_investment_expense = (
            monthly_investment_retirement +
            medical_results.get('monthly_investment_medical_retirement', 0) +
            monthly_investment_education + monthly_investment_marriage +
            hlv_results.get('monthly_investment_insurance_expense', 0) +
            monthly_investment_emergency)

        # ── 9. FINANCIAL HEALTH SCORE ──
        financial_health_score = 0
        score_details = []

        # Savings rate (30 pts)
        if savings_rate >= 20:
            financial_health_score += 30
            score_details.append(("Savings Rate (≥20%)", 30, 30))
        elif savings_rate >= 10:
            financial_health_score += 20
            score_details.append(("Savings Rate (10-19%)", savings_rate, 20))
        else:
            financial_health_score += 10
            score_details.append(("Savings Rate (<10%)", savings_rate, 10))

        # Net worth (30 pts)
        if net_worth > annual_income * 5:
            financial_health_score += 30
            score_details.append(("Net Worth (>5x income)", f"Rs {int(net_worth):,}", 30))
        elif net_worth > annual_income * 2:
            financial_health_score += 20
            score_details.append(("Net Worth (2-5x income)", f"Rs {int(net_worth):,}", 20))
        else:
            financial_health_score += 10
            score_details.append(("Net Worth (<2x income)", f"Rs {int(net_worth):,}", 10))

        # Insurance (20 pts)
        if hlv_results.get('additional_life_cover_needed_income', 0) <= 0:
            financial_health_score += 20
            score_details.append(("Insurance Coverage (Full)", "Fully covered", 20))
        elif hlv_results.get('additional_life_cover_needed_income', 0) < hlv_results.get('hlv_income_method', 0) * 0.3:
            financial_health_score += 10
            score_details.append(("Insurance Coverage (Partial)", f"Rs {hlv_results.get('additional_life_cover_needed_income', 0):,} gap", 10))
        else:
            score_details.append(("Insurance Coverage (Inadequate)", f"Rs {hlv_results.get('additional_life_cover_needed_income', 0):,} gap", 0))

        # Retirement readiness (20 pts)
        if retirement_readiness > 50:
            financial_health_score += 20
            score_details.append(("Retirement Readiness (>50%)", f"{retirement_readiness}%", 20))
        elif retirement_readiness > 25:
            financial_health_score += 10
            score_details.append(("Retirement Readiness (25-50%)", f"{retirement_readiness}%", 10))
        else:
            score_details.append(("Retirement Readiness (<25%)", f"{retirement_readiness}%", 0))

        # Emergency fund (10 pts)
        if emergency_fund_shortfall <= 0:
            financial_health_score += 10
            score_details.append(("Emergency Fund (Adequate)", "Fully funded", 10))
        else:
            score_details.append(("Emergency Fund (Shortfall)", f"Rs {emergency_fund_shortfall:,} short", 0))

        financial_health_score = min(100, financial_health_score)

        # ── BUILD RESULT ──
        return {
            'client_age': int(client_age),
            'total_expenses': int(annual_expenses),
            'net_worth': int(net_worth),
            'asset_liability_ratio': 1 if net_worth > 0 else 0,
            'savings_rate': int(savings_rate),
            'debt_to_income_ratio': 0,

            # HLV
            'hlv_income_method': int(hlv_results.get('hlv_income_method', 0)),
            'hlv_expense_method': int(hlv_results.get('hlv_expense_method', 0)),
            'years_considered_income': int(hlv_results.get('years_considered_income', 0)),
            'years_considered_expense': int(hlv_results.get('years_considered_expense', 0)),
            'spouse_life_expectancy_used': int(hlv_results.get('spouse_life_expectancy_used', 0)),
            'net_hlv_income': int(hlv_results.get('net_hlv_income', 0)),
            'net_hlv_expense': int(hlv_results.get('net_hlv_expense', 0)),
            'additional_life_cover_needed_income': int(hlv_results.get('additional_life_cover_needed_income', 0)),
            'additional_life_cover_needed_expense': int(hlv_results.get('additional_life_cover_needed_expense', 0)),
            'monthly_investment_insurance_income': int(hlv_results.get('monthly_investment_insurance_income', 0)),
            'monthly_investment_insurance_expense': int(hlv_results.get('monthly_investment_insurance_expense', 0)),

            # Retirement
            'retirement_corpus_at_retirement': int(retirement_corpus_at_retirement),
            'existing_retirement_savings': int(existing_retirement_savings),
            'future_value_existing_savings': int(future_value_existing_savings),
            'net_retirement_corpus_needed': int(net_retirement_corpus_needed),
            'years_to_retirement': int(years_to_retirement),
            'remaining_years': int(max(0, int(assumptions.get('le_client', 85)) - client_age)),
            'monthly_investment_retirement': int(monthly_investment_retirement),
            'retirement_readiness': int(retirement_readiness),

            # Medical
            'medical_corpus_today': int(medical_results.get('medical_corpus_today', 0)),
            'medical_corpus_at_retirement': int(medical_results.get('medical_corpus_at_retirement', 0)),
            'medical_corpus_at_life_expectancy': int(medical_results.get('medical_corpus_at_life_expectancy', 0)),
            'total_coverage_at_retirement': int(medical_results.get('total_coverage_at_retirement', 0)),
            'total_coverage_at_life_expectancy': int(medical_results.get('total_coverage_at_life_expectancy', 0)),
            'balance_needed_at_retirement': int(medical_results.get('balance_needed_at_retirement', 0)),
            'balance_needed_at_life_expectancy': int(medical_results.get('balance_needed_at_life_expectancy', 0)),
            'monthly_investment_medical_retirement': int(medical_results.get('monthly_investment_medical_retirement', 0)),
            'monthly_investment_medical_life_expectancy': int(medical_results.get('monthly_investment_medical_life_expectancy', 0)),

            # Child Goals
            'education_corpus_today': int(assumptions.get('child_education_corpus', 0)),
            'education_future_needed': int(education_future_needed),
            'education_net_corpus': int(net_education_corpus),
            'marriage_corpus_today': int(assumptions.get('child_marriage_corpus', 0)),
            'marriage_future_needed': int(marriage_future_needed),
            'marriage_net_corpus': int(net_marriage_corpus),
            'monthly_investment_education': int(monthly_investment_education),
            'monthly_investment_marriage': int(monthly_investment_marriage),
            'fv_allocated_education': int(fv_allocated_education),
            'fv_allocated_marriage': int(fv_allocated_marriage),
            'allocated_investment_education': int(allocated_investment_education),
            'allocated_investment_marriage': int(allocated_investment_marriage),

            # Emergency Fund
            'emergency_fund_needed': int(emergency_fund_needed),
            'emergency_fund_shortfall': int(emergency_fund_shortfall),
            'monthly_investment_emergency': int(monthly_investment_emergency),

            # Summary
            'cash_flow_analysis': cash_flow,
            'financial_health_score': int(financial_health_score),
            'financial_health_score_details': score_details,
            'total_monthly_investment_income': int(total_monthly_investment_income),
            'total_monthly_investment_expense': int(total_monthly_investment_expense),
            'current_medical_cover': int(medical_results.get('current_medical_cover', 0)),
            'medical_bonus_years': int(medical_results.get('medical_bonus_years', 0)),
            'medical_bonus_percentage': float(medical_results.get('medical_bonus_percentage', 0)),
        }
