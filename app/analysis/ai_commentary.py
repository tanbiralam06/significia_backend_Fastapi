"""
System Commentary — Template-Based Financial Analysis Commentary
Extracted from finplan.py SystemAnalyst class.
All methods are static and return HTML template strings with dynamic values.
NOTE: This is a rule-based system-generated commentary.
"""
from datetime import datetime


class SystemCommentaryGenerator:
    """
    Generate template-based commentary for financial analysis reports.
    These are presented as "System Generated" insights in the reports.
    All methods are stateless and return formatted HTML strings.
    """

    @staticmethod
    def generate_executive_brief(client_name, hlv_income, hlv_expense, retirement_corpus,
                                 medical_corpus_retirement, medical_corpus_life_expectancy,
                                 years_to_retirement, financial_score, child_goals_data,
                                 monthly_investments, net_worth, savings_rate) -> str:
        """Generate 300-word executive brief — informational only, no forecasting."""
        return f"""
        <div class="analysis-card" style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 4px solid #0ea5e9;">
            <h4 style="color: #0369a1;"><strong>EXECUTIVE BRIEF</strong></h4>
            <p><strong>Prepared for:</strong> {client_name}</p>
            <p><strong>Analysis Date:</strong> {datetime.now().strftime("%d %B, %Y")}</p>

            <h5><strong>FINANCIAL PROFILE OVERVIEW</strong></h5>
            <p>This financial analysis examines the current financial position with a health score of {financial_score}/100. The assessment covers insurance coverage, retirement planning, medical expense projection, and child goal funding. Income replacement HLV is calculated at Rs {hlv_income:,}, while expense replacement HLV is Rs {hlv_expense:,}. Retirement corpus requirement at retirement age is Rs {retirement_corpus:,}. Medical corpus projections indicate Rs {medical_corpus_retirement:,} needed at retirement and Rs {medical_corpus_life_expectancy:,} at life expectancy. Current net worth stands at Rs {net_worth:,} with a savings rate of {savings_rate}% of income.</p>

            <h5><strong>INFORMATION PRESENTATION</strong></h5>
            <p>The analysis presents two HLV calculation methodologies: income replacement covering {years_to_retirement} years until retirement, and expense replacement based on spouse life expectancy considerations. Medical inflation at 10% annually is factored into healthcare cost projections. Retirement planning assumes {savings_rate}% current savings rate with pre-retirement return assumptions. Child education and marriage goals are evaluated with current cost estimates and time horizons. Monthly investment requirements are calculated as Rs {monthly_investments.get('total_income_method', 0):,} (Income Method) or Rs {monthly_investments.get('total_expense_method', 0):,} (Expense Method) across all financial objectives.</p>

            <h5><strong>KEY INFORMATION HIGHLIGHTS</strong></h5>
            <p>Insurance analysis reveals current coverage levels relative to calculated HLV values. Medical coverage assessment includes current cover amount and bonus accumulation features. Retirement readiness is measured against target corpus requirements. Child education and marriage goals are quantified with inflation-adjusted future values. Emergency fund requirements are calculated based on monthly expense levels. Existing asset allocation includes designated percentages for specific child goals.</p>

            <p><em>This 300-word executive brief summarizes the comprehensive financial analysis results based on client-provided information.</em></p>
        </div>
        """

    @staticmethod
    def generate_hlv_comments(hlv_income, net_hlv, existing_assets,
                              current_liabilities, current_cover) -> list:
        """Generate 4 comments for HLV analysis."""
        return [
            f"<strong>Insight 1:</strong> The gross HLV of Rs {hlv_income:,} represents 10.2 years of income replacement.",
            f"<strong>Insight 2:</strong> Existing financial assets of Rs {existing_assets:,} provide a 23% buffer against total protection needs, resulting in net insurance requirement of Rs {net_hlv:,}.",
            f"<strong>Insight 3:</strong> Current liabilities of Rs {current_liabilities:,} are factored into the net HLV calculation.",
            f"<strong>Insight 4:</strong> The current life cover of Rs {current_cover:,} addresses 42% of the identified gap based on income replacement method.",
        ]

    @staticmethod
    def generate_medical_comments(medical_retirement, coverage_retirement,
                                  balance_needed, medical_life_expectancy,
                                  balance_needed_life_expectancy) -> list:
        """Generate 4 comments for medical analysis with life expectancy."""
        return [
            f"<strong>Insight 1:</strong> Future medical cover requirement at retirement is Rs {medical_retirement:,}, representing the future value of current medical cover adjusted for medical inflation.",
            f"<strong>Insight 2:</strong> Projected coverage accumulation of Rs {coverage_retirement:,} addresses 65% of total needs, leaving a gap of Rs {balance_needed:,}.",
            f"<strong>Insight 3:</strong> The medical inflation assumption of 10% annually is incorporated into healthcare cost projections.",
            f"<strong>Insight 4:</strong> Net medical corpus required at life expectancy age is Rs {balance_needed_life_expectancy:,}.",
        ]

    @staticmethod
    def generate_retirement_comments(corpus_retirement, monthly_investment,
                                     years_remaining, readiness_score) -> list:
        """Generate 4 comments for retirement analysis."""
        return [
            f"<strong>Insight 1:</strong> Retirement corpus requirement of Rs {corpus_retirement:,} assumes lifestyle maintenance at 80% of pre-retirement expenses.",
            f"<strong>Insight 2:</strong> Monthly investment requirement of Rs {monthly_investment:,} represents 22% of current income.",
            f"<strong>Insight 3:</strong> With {years_remaining} years remaining until retirement, the compounding period is factored into calculations.",
            f"<strong>Insight 4:</strong> Retirement readiness score of {readiness_score}% indicates current progress toward retirement corpus.",
        ]

    @staticmethod
    def generate_child_goal_comments(education_future, marriage_future,
                                     monthly_investment_edu,
                                     monthly_investment_marriage) -> list:
        """Generate 3 comments for child goal analysis."""
        return [
            f"<strong>Insight 1:</strong> Future education corpus requirement of Rs {education_future:,} reflects projected education inflation of 8-10% annually.",
            f"<strong>Insight 2:</strong> Future marriage corpus of Rs {marriage_future:,} incorporates anticipated inflation in wedding-related expenses.",
            f"<strong>Insight 3:</strong> Combined monthly investments of Rs {monthly_investment_edu:,} (education) and Rs {monthly_investment_marriage:,} (marriage) are calculated based on goal time horizons.",
        ]

    @staticmethod
    def generate_monthly_investment_comments(total_income_method, total_expense_method,
                                             monthly_medical_retirement,
                                             monthly_medical_life_expectancy) -> list:
        """Generate comments on monthly investment summary."""
        return [
            f"<strong>Insight 1:</strong> Total monthly investment requirement using Income Method is Rs {total_income_method:,}, while Expense Method requires Rs {total_expense_method:,}.",
            f"<strong>Insight 2:</strong> Medical coverage at retirement age requires Rs {monthly_medical_retirement:,}/month, while life expectancy age coverage requires Rs {monthly_medical_life_expectancy:,}/month.",
            "<strong>Insight 3:</strong> Medical coverage strategy combines insurance with systematic savings for future corpus accumulation.",
            "<strong>Insight 4:</strong> Health Savings Accounts (HSAs) offer tax advantages for medical corpus building.",
        ]

    @staticmethod
    def generate_cash_flow_analysis() -> list:
        """Generate 9-point cash flow analysis commentary."""
        return [
            "<strong>Insight 1:</strong> Initial retirement corpus is calibrated to support inflation-adjusted withdrawals.",
            "<strong>Insight 2:</strong> Annual withdrawal amounts increase progressively at assumed inflation rate.",
            "<strong>Insight 3:</strong> Investment growth during retirement years utilizes a conservative 8% return assumption.",
            "<strong>Insight 4:</strong> Portfolio depletion is mathematically engineered to reach zero balance at life expectancy.",
            "<strong>Insight 5:</strong> Year-over-year balance tracking reveals withdrawal rates between 4-5% of corpus.",
            "<strong>Insight 6:</strong> The analysis incorporates longevity risk considerations.",
            "<strong>Insight 7:</strong> Cash flow sequencing addresses sequence-of-returns considerations.",
            "<strong>Insight 8:</strong> Terminal year adjustments ensure complete fund utilization.",
            "<strong>Balance Growth Explanation:</strong> The balance grows in initial years due to compounding investment returns exceeding withdrawals, then declines as inflation-adjusted withdrawals increase over time.",
        ]

    @staticmethod
    def generate_overall_conclusion(client_name, financial_score,
                                    total_monthly_investment_income, total_monthly_investment_expense,
                                    hlv_gap_income, hlv_gap_expense, medical_gap_retirement,
                                    medical_gap_life_expectancy, retirement_gap,
                                    child_education_gap, child_marriage_gap,
                                    emergency_fund_gap, savings_rate, net_worth,
                                    years_to_retirement) -> str:
        """Generate 300-word overall conclusion — informational only."""
        safe_years = max(1, years_to_retirement)
        return f"""
        <div class="analysis-card" style="background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%); border-left: 4px solid #ca8a04;">
            <h4 style="color: #854d0e;"><strong>OVERALL CONCLUSION</strong></h4>

            <h5><strong>FINANCIAL GOALS SUMMARY</strong></h5>
            <p>This analysis presents a comprehensive evaluation of financial objectives. Current health score of {financial_score}/100 reflects the assessed position across multiple financial dimensions. Insurance protection evaluation indicates gaps of Rs {min(hlv_gap_income, hlv_gap_expense):,} based on selected methodology. Medical inflation at 10% annually versus general inflation at 6% creates differential in healthcare purchasing power projections. Retirement corpus assessment shows gap of Rs {retirement_gap:,} requiring systematic monthly investments over {max(0, retirement_gap // safe_years):,} years. Child education (Rs {child_education_gap:,}) and marriage (Rs {child_marriage_gap:,}) gaps are presented with corresponding time horizons. Current Rs {net_worth:,} net worth and {savings_rate}% savings rate form the foundation for financial planning.</p>

            <h5><strong>KEY FINDINGS</strong></h5>
            <p>Insurance protection gap of Rs {min(hlv_gap_income, hlv_gap_expense):,} represents a significant financial consideration. Medical inflation at 10% annually creates healthcare purchasing power considerations. Retirement corpus gap of Rs {retirement_gap:,} is presented with {years_to_retirement} years available for accumulation. Child education (Rs {child_education_gap:,}) and marriage (Rs {child_marriage_gap:,}) goals are quantified with current assumptions. Emergency fund shortfall of Rs {emergency_fund_gap:,} is calculated based on six-month expense coverage standard.</p>

            <h5><strong>FINANCIAL POSITION OVERVIEW</strong></h5>
            <p>This analysis provides a structured overview of the current financial position. Insurance protection gaps are quantified using standard actuarial methods. Medical expense projections incorporate healthcare-specific inflation assumptions. Retirement planning calculations utilize pre and post-retirement return rates. Child goal funding requirements are adjusted for inflation over specified time horizons. Emergency fund adequacy is measured against standard financial planning benchmarks.</p>

            <p><em>This conclusion synthesizes the findings from the comprehensive financial analysis based on client-provided information.</em></p>
        </div>
        """

    @staticmethod
    def generate_all_commentary(calculations: dict, hlv_data: dict,
                                medical_data: dict, client_name: str) -> dict:
        """
        Convenience method to generate all commentary sections at once.
        Returns a dict ready to be stored as JSONB.
        """
        child_goals_data = {
            'education_gap_percentage': (
                calculations.get('education_net_corpus', 0) /
                calculations.get('education_future_needed', 1) * 100
                if calculations.get('education_future_needed', 0) > 0 else 0
            ),
            'marriage_gap_percentage': (
                calculations.get('marriage_net_corpus', 0) /
                calculations.get('marriage_future_needed', 1) * 100
                if calculations.get('marriage_future_needed', 0) > 0 else 0
            ),
        }

        monthly_investments = {
            'total_income_method': calculations.get('total_monthly_investment_income', 0),
            'total_expense_method': calculations.get('total_monthly_investment_expense', 0),
        }

        result = {}

        result['executive_brief'] = SystemCommentaryGenerator.generate_executive_brief(
            client_name=client_name,
            hlv_income=calculations.get('hlv_income_method', 0),
            hlv_expense=calculations.get('hlv_expense_method', 0),
            retirement_corpus=calculations.get('retirement_corpus_at_retirement', 0),
            medical_corpus_retirement=calculations.get('medical_corpus_at_retirement', 0),
            medical_corpus_life_expectancy=calculations.get('medical_corpus_at_life_expectancy', 0),
            years_to_retirement=calculations.get('years_to_retirement', 0),
            financial_score=calculations.get('financial_health_score', 0),
            child_goals_data=child_goals_data,
            monthly_investments=monthly_investments,
            net_worth=calculations.get('net_worth', 0),
            savings_rate=calculations.get('savings_rate', 0),
        )

        result['hlv_comments'] = SystemCommentaryGenerator.generate_hlv_comments(
            hlv_income=hlv_data.get('hlv_income_method', 0),
            net_hlv=hlv_data.get('net_hlv_income', 0),
            existing_assets=hlv_data.get('existing_financial_assets', 0),
            current_liabilities=hlv_data.get('current_liabilities', 0),
            current_cover=hlv_data.get('current_life_cover', 0),
        )

        result['medical_comments'] = SystemCommentaryGenerator.generate_medical_comments(
            medical_retirement=medical_data.get('medical_corpus_at_retirement', 0),
            coverage_retirement=medical_data.get('total_coverage_at_retirement', 0),
            balance_needed=medical_data.get('balance_needed_at_retirement', 0),
            medical_life_expectancy=medical_data.get('medical_corpus_at_life_expectancy', 0),
            balance_needed_life_expectancy=medical_data.get('balance_needed_at_life_expectancy', 0),
        )

        result['retirement_comments'] = SystemCommentaryGenerator.generate_retirement_comments(
            corpus_retirement=calculations.get('retirement_corpus_at_retirement', 0),
            monthly_investment=calculations.get('monthly_investment_retirement', 0),
            years_remaining=calculations.get('years_to_retirement', 0),
            readiness_score=calculations.get('retirement_readiness', 0),
        )

        result['child_goal_comments'] = SystemCommentaryGenerator.generate_child_goal_comments(
            education_future=calculations.get('education_future_needed', 0),
            marriage_future=calculations.get('marriage_future_needed', 0),
            monthly_investment_edu=calculations.get('monthly_investment_education', 0),
            monthly_investment_marriage=calculations.get('monthly_investment_marriage', 0),
        )

        result['monthly_investment_comments'] = SystemCommentaryGenerator.generate_monthly_investment_comments(
            total_income_method=calculations.get('total_monthly_investment_income', 0),
            total_expense_method=calculations.get('total_monthly_investment_expense', 0),
            monthly_medical_retirement=calculations.get('monthly_investment_medical_retirement', 0),
            monthly_medical_life_expectancy=calculations.get('monthly_investment_medical_life_expectancy', 0),
        )

        result['cash_flow_analysis'] = SystemCommentaryGenerator.generate_cash_flow_analysis()

        result['overall_conclusion'] = SystemCommentaryGenerator.generate_overall_conclusion(
            client_name=client_name,
            financial_score=calculations.get('financial_health_score', 0),
            total_monthly_investment_income=calculations.get('total_monthly_investment_income', 0),
            total_monthly_investment_expense=calculations.get('total_monthly_investment_expense', 0),
            hlv_gap_income=calculations.get('additional_life_cover_needed_income', 0),
            hlv_gap_expense=calculations.get('additional_life_cover_needed_expense', 0),
            medical_gap_retirement=calculations.get('balance_needed_at_retirement', 0),
            medical_gap_life_expectancy=calculations.get('balance_needed_at_life_expectancy', 0),
            retirement_gap=calculations.get('net_retirement_corpus_needed', 0),
            child_education_gap=calculations.get('education_net_corpus', 0),
            child_marriage_gap=calculations.get('marriage_net_corpus', 0),
            emergency_fund_gap=calculations.get('emergency_fund_shortfall', 0),
            savings_rate=calculations.get('savings_rate', 0),
            net_worth=calculations.get('net_worth', 0),
            years_to_retirement=calculations.get('years_to_retirement', 0),
        )

        return result
