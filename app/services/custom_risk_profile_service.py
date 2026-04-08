import json
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Any, Dict

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.client import ClientProfile
from app.models.risk_profile import RiskQuestionnaire, CustomRiskAssessment, ClientRiskMaster
from app.models.ia_master import AuditTrail as IAMasterAuditTrail
from app.schemas.custom_risk_profile_schema import (
    RiskQuestionnaireCreate, 
    RiskQuestionnaireUpdate, 
    CustomRiskAssessmentCreate,
    RiskQuestionnaireResponse
)

class CustomRiskProfileService:
    @staticmethod
    def create_questionnaire(db: Session, payload: RiskQuestionnaireCreate) -> RiskQuestionnaire:
        # Calculate max possible score
        total_max = 0
        for q in payload.questions:
            if q.options:
                option_scores = [o.score for o in q.options]
                total_max += max(option_scores) if option_scores else 0
        
        questionnaire = RiskQuestionnaire(
            portfolio_name=payload.portfolio_name,
            questions=[q.model_dump() for q in payload.questions],
            categories=[c.model_dump() for c in payload.categories],
            status=payload.status,
            max_possible_score=total_max
        )
        db.add(questionnaire)
        db.commit()
        db.refresh(questionnaire)
        return questionnaire

    @staticmethod
    def list_questionnaires(db: Session, status: Optional[str] = None) -> List[RiskQuestionnaire]:
        query = select(RiskQuestionnaire)
        if status:
            query = query.where(RiskQuestionnaire.status == status)
        return db.execute(query).scalars().all()

    @staticmethod
    def get_questionnaire(db: Session, q_id: uuid.UUID) -> Optional[RiskQuestionnaire]:
        return db.execute(select(RiskQuestionnaire).where(RiskQuestionnaire.id == q_id)).scalar_one_or_none()

    @staticmethod
    def update_questionnaire(db: Session, q_id: uuid.UUID, payload: RiskQuestionnaireUpdate) -> Optional[RiskQuestionnaire]:
        questionnaire = CustomRiskProfileService.get_questionnaire(db, q_id)
        if not questionnaire:
            return None
        
        update_data = payload.model_dump(exclude_unset=True)
        
        # If questions change, recalculate max possible score
        if "questions" in update_data:
            total_max = 0
            for q in payload.questions:
                if q.options:
                    option_scores = [o.score for o in q.options]
                    total_max += max(option_scores) if option_scores else 0
            update_data["max_possible_score"] = total_max
            update_data["questions"] = [q.model_dump() for q in payload.questions]
        
        if "categories" in update_data:
            update_data["categories"] = [c.model_dump() for c in payload.categories]

        for key, value in update_data.items():
            setattr(questionnaire, key, value)
        
        questionnaire.updated_at = datetime.utcnow()
        db.add(questionnaire)
        db.commit()
        db.refresh(questionnaire)
        return questionnaire

    @staticmethod
    def submit_assessment(
        db: Session, 
        payload: CustomRiskAssessmentCreate,
        user_ip: str,
        user_agent: str
    ) -> CustomRiskAssessment:
        # 1. Fetch Questionnaire
        questionnaire = CustomRiskProfileService.get_questionnaire(db, payload.questionnaire_id)
        if not questionnaire:
            raise ValueError("Questionnaire not found")
        
        # 2. Fetch Client
        client = db.execute(
            select(ClientProfile).where(ClientProfile.client_code == payload.client_code)
        ).scalar_one_or_none()
        if not client:
            raise ValueError(f"Client {payload.client_code} not found")
        
        # 3. Calculate Score
        total_score = 0
        for q_id, resp in payload.responses.items():
            total_score += resp.get("score", 0)
        
        # 4. Determine Category
        category_name = "Unknown"
        for cat in questionnaire.categories:
            if cat["min_score"] <= total_score <= cat["max_score"]:
                category_name = cat["name"]
                break
        
        # 5. Create Assessment
        assessment = CustomRiskAssessment(
            questionnaire_id=payload.questionnaire_id,
            client_id=client.id,
            responses=payload.responses,
            total_score=total_score,
            category_name=category_name,
            discussion_notes=payload.discussion_notes
        )
        db.add(assessment)
        db.flush()
        
        # 6. Update ClientRiskMaster
        existing_risk_master = db.execute(
            select(ClientRiskMaster).where(ClientRiskMaster.client_id == client.id)
        ).scalar_one_or_none()
        
        if existing_risk_master:
            existing_risk_master.category_name = category_name
            existing_risk_master.portfolio_name = questionnaire.portfolio_name
            existing_risk_master.submitted_at = datetime.utcnow()
        else:
            risk_master = ClientRiskMaster(
                client_id=client.id,
                ia_registration_number=client.advisor_name,
                category_name=category_name,
                portfolio_name=questionnaire.portfolio_name,
                submitted_at=datetime.utcnow()
            )
            db.add(risk_master)
        
        # 7. Update client profile for quick lookup
        client.risk_profile = category_name
        
        # 8. Audit Log
        audit = IAMasterAuditTrail(
            action_type="CUSTOM_RISK_ASSESSMENT_SAVE",
            table_name="custom_risk_assessments",
            record_id=str(assessment.id),
            changes=json.dumps({
                "client_code": payload.client_code,
                "score": total_score,
                "category": category_name,
                "portfolio": questionnaire.portfolio_name
            }),
            user_ip=user_ip,
            user_agent=user_agent
        )
        db.add(audit)
        
        db.commit()
        db.refresh(assessment)
        return assessment

    @staticmethod
    def list_client_assessments(db: Session, client_id: Optional[uuid.UUID] = None) -> List[Any]:
        query = select(
            CustomRiskAssessment, 
            RiskQuestionnaire.portfolio_name, 
            ClientProfile.client_name, 
            ClientProfile.client_code
        ).join(RiskQuestionnaire, CustomRiskAssessment.questionnaire_id == RiskQuestionnaire.id)\
         .join(ClientProfile, CustomRiskAssessment.client_id == ClientProfile.id)
        
        if client_id:
            query = query.where(CustomRiskAssessment.client_id == client_id)
        
        query = query.order_by(CustomRiskAssessment.submitted_at.desc())
        
        results = db.execute(query).all()
        
        output = []
        for row in results:
            assessment = row[0]
            assessment.portfolio_name = row.portfolio_name
            assessment.client_name = row.client_name
            assessment.client_code = row.client_code
            output.append(assessment)
            
        return output
