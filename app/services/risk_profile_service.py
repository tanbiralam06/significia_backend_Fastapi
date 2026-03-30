import json
import uuid
from datetime import datetime
from typing import Dict, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import ClientProfile
from app.models.risk_profile import RiskAssessment, ClientRiskMaster
from app.models.ia_master import AuditTrail as IAMasterAuditTrail
from app.schemas.risk_profile_schema import RiskAssessmentCreate, RiskAssessmentAnswers

# Constants from standalone risk_profile.py
SCORING_RULES = {
    'q1': {'a': 8, 'b': 0, 'c': 4},
    'q2': {
        'a': {'A': 0, 'B': 1, 'C': 2},
        'b': {'A': 1, 'B': 1, 'C': 0},
        'c': {'A': 2, 'B': 1, 'C': 0},
        'd': {'A': 2, 'B': 1, 'C': 0},
        'e': {'A': 2, 'B': 1, 'C': 0},
        'f': {'A': 0, 'B': 1, 'C': 2},
        'g': {'A': 0, 'B': 1, 'C': 2},
        'h': {'A': 0, 'B': 1, 'C': 2},
    },
    'q3': {'a': 6, 'b': 3, 'c': 1},
    'q4': {'A': 5, 'B': 0},
    'q5': {'a': 0, 'b': 5, 'c': 5},
    'q6': {'a': 6, 'b': 0, 'c': 3, 'd': 0, 'e': 5},
    'q7': {'A': 5, 'B': 0},
    'q8': {'a': 7, 'b': 5, 'c': 3, 'd': 2, 'e': 0},
    'q9': {'a': 0, 'b': 2, 'c': 4, 'd': 5, 'e': 7},
    'q10': {'a': 2, 'b': 4, 'c': 5, 'd': 7, 'e': 8},
    'q11': {'a': 5, 'b': 3, 'c': 2, 'd': 0},
    'q12': {'a': 1, 'b': 2, 'c': 3, 'd': 4},
    'q13': {'a': 4, 'b': 3, 'c': 2, 'd': 1},
    'q14': {'a': 4, 'b': 2, 'c': 1},
    'q15': {'a': 5, 'b': 1},
    'q16': {'a': 5, 'b': 3, 'c': 1}
}

RISK_TIERS = [
    [0, 10, "Ultra Conservative", "Capital preservation focus, minimal volatility tolerance"],
    [11, 25, "Conservative", "Stable investments with low volatility preference"],
    [26, 45, "Moderate", "Balanced approach to growth and stability"],
    [46, 65, "Moderately Aggressive", "Growth-oriented with moderate volatility acceptance"],
    [66, 85, "Aggressive", "High growth focus with volatility acceptance"],
    [86, 100, "Highly Aggressive", "Maximum growth pursuit with high risk tolerance"]
]

class RiskProfileService:
    @staticmethod
    def calculate_scores(answers: RiskAssessmentAnswers) -> Tuple[int, Dict]:
        total_score = 0
        question_scores = {}
        
        # Helper to convert pydantic to dict for iteration
        ans_dict = answers.model_dump()

        # Simple keys
        for q in ['q1', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10', 'q11', 'q12', 'q13', 'q14', 'q15', 'q16']:
            val = ans_dict.get(q)
            score = SCORING_RULES[q].get(val, 0)
            total_score += score
            max_val = max(SCORING_RULES[q].values())
            question_scores[q] = {'score': score, 'max': max_val}

        # Q2 Factor mapping
        q2_total = 0
        q2_details = {}
        q2_answers = ans_dict.get('q2', {})
        for factor, rating in q2_answers.items():
            factor_score = SCORING_RULES['q2'][factor].get(rating, 0)
            q2_total += factor_score
            q2_details[factor] = {'rating': rating, 'score': factor_score, 'max': 2}
        
        total_score += q2_total
        question_scores['q2'] = {'score': q2_total, 'max': 16, 'details': q2_details}

        return total_score, question_scores

    @staticmethod
    def determine_risk_tier(score: int) -> Tuple[str, str]:
        for tier in RISK_TIERS:
            min_score, max_score, tier_name, recommendation = tier
            if min_score <= score <= max_score:
                return tier_name, recommendation
        return "Unknown", "No recommendation available"

    @staticmethod
    def save_assessment(
        db: Session, 
        payload: RiskAssessmentCreate,
        user_ip: str,
        user_agent: str
    ) -> Tuple[uuid.UUID, uuid.UUID, int, str, str, str]:
        # 1. Fetch Client by client_code
        client = db.execute(
            select(ClientProfile).where(ClientProfile.client_code == payload.client_code)
        ).scalar_one_or_none()
        
        if not client:
            raise ValueError(f"Client with code {payload.client_code} not found")

        # 2. Compute Score
        total_score, question_scores = RiskProfileService.calculate_scores(payload.answers)
        risk_tier, recommendation = RiskProfileService.determine_risk_tier(total_score)

        # 3. Create RiskAssessment
        assessment = RiskAssessment(
            client_id=client.id,
            q1_interest_choice=payload.answers.q1,
            q2_importance_factors=payload.answers.q2.model_dump(),
            q3_probability_bet=payload.answers.q3,
            q4_portfolio_choice=payload.answers.q4,
            q5_loss_behavior=payload.answers.q5,
            q6_market_reaction=payload.answers.q6,
            q7_fund_selection=payload.answers.q7,
            q8_experience_level=payload.answers.q8,
            q9_time_horizon=payload.answers.q9,
            q10_net_worth=payload.answers.q10,
            q11_age_range=payload.answers.q11,
            q12_income_range=payload.answers.q12,
            q13_expense_range=payload.answers.q13,
            q14_dependents=payload.answers.q14,
            q15_active_loan=payload.answers.q15,
            q16_investment_objective=payload.answers.q16,
            calculated_score=total_score,
            assigned_risk_tier=risk_tier,
            tier_recommendation=recommendation,
            disclaimer_text=payload.disclaimer_text,
            discussion_notes=payload.discussion_notes,
            form_name=payload.form_name,
            question_scores=question_scores
        )
        db.add(assessment)
        db.flush()

        # 4. Update ClientRiskMaster
        # Check if an existing entry exists to update or create new
        existing_risk_master = db.execute(
            select(ClientRiskMaster).where(ClientRiskMaster.client_id == client.id)
        ).scalar_one_or_none()
        
        if existing_risk_master:
            existing_risk_master.category_name = risk_tier
            existing_risk_master.ia_registration_number = client.advisor_name # Assuming advisor name maps or needs lookup
            existing_risk_master.submitted_at = datetime.utcnow()
            risk_master = existing_risk_master
        else:
            risk_master = ClientRiskMaster(
                client_id=client.id,
                ia_registration_number=client.advisor_name,
                category_name=risk_tier,
                portfolio_name="client_assessments",
                submitted_at=datetime.utcnow()
            )
            db.add(risk_master)
            db.flush()

        # 5. Log Audit
        audit = IAMasterAuditTrail(
            action_type="RISK_ASSESSMENT_SAVE",
            table_name="risk_assessments",
            record_id=str(assessment.id),
            changes=json.dumps({
                "client_code": payload.client_code,
                "score": total_score,
                "tier": risk_tier,
                "form_name": payload.form_name
            }),
            user_ip=user_ip,
            user_agent=user_agent
        )
        db.add(audit)
        
        db.commit()
        
        return (
            assessment.id, 
            risk_master.id, 
            total_score, 
            risk_tier, 
            payload.client_code, 
            risk_master.ia_registration_number
        )

    @staticmethod
    def list_assessments(db: Session) -> List[dict]:
        """
        Retrieves all risk assessments, joining with client info.
        """
        results = db.execute(
            select(RiskAssessment, ClientProfile.client_name, ClientProfile.client_code)
            .join(ClientProfile, RiskAssessment.client_id == ClientProfile.id)
            .order_by(RiskAssessment.assessment_timestamp.desc())
        ).all()
        
        output = []
        for row in results:
            assessment = row[0]
            assessment.client_name = row.client_name
            assessment.client_code = row.client_code
            output.append(assessment)
            
        return output
