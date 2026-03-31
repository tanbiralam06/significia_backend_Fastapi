import json
import uuid
from datetime import datetime
from typing import Dict, Tuple, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.client import ClientProfile
from app.models.risk_profile import ClientRiskMaster
from app.models.asset_allocation import AssetAllocation
from app.models.ia_master import AuditTrail as IAMasterAuditTrail, IAMaster
from app.schemas.asset_allocation import AssetAllocationCreate

class AssetAllocationService:
    @staticmethod
    def generate_system_conclusion(client_name: str, risk_tier: str, allocation_data: Dict) -> str:
        """
        Generate system conclusion based on allocation data.
        Ported from standalone asset_allocation.py.
        """
        equities = allocation_data.get('equities_percentage', 0.0)
        debt = allocation_data.get('debt_securities_percentage', 0.0)
        commodities = allocation_data.get('commodities_percentage', 0.0)
        
        return f"""STRATEGIC IMPORTANCE OF ASSET ALLOCATION AND REBALANCING

Client: {client_name} | Risk Tier: {risk_tier} | Edited Allocation: Equities {equities:.1f}% | Debt {debt:.1f}% | Commodities {commodities:.1f}%

THE IMPORTANCE OF ASSET ALLOCATION AND REBALANCING:

Asset allocation is a fundamental determinant of investment outcomes. The edited allocation represents a balance between growth (equities), stability (debt), and inflation protection (commodities). Periodic rebalancing helps maintain intended risk profiles despite market fluctuations, supporting disciplined investment practices.

HOW THIS EDITED ALLOCATION FUNCTIONS:

The {equities:.1f}% equity allocation provides calibrated exposure to long-term capital appreciation while respecting {risk_tier} risk boundaries. The {debt:.1f}% debt allocation provides stability during market downturns and can help meet short-to-medium-term obligations. The {commodities:.1f}% commodities allocation adds diversification that typically behaves differently from traditional financial assets, offering potential inflation protection.

CONSIDERATIONS FOR THIS ALLOCATION:

This allocation is designed to work across economic cycles. The debt component serves dual functions of income generation and capital preservation. The commodities allocation may help preserve purchasing power during periods of currency weakness or inflation.

This edited asset allocation represents an evolution of investment strategy. Regular reviews are essential as personal circumstances, financial objectives, and market conditions evolve. Maintaining an emergency fund outside this investment portfolio is recommended."""

    @staticmethod
    def validate_client_for_allocation(db: Session, client_code: str) -> Dict:
        """
        Validates client code and returns profile/risk data.
        """
        client = db.execute(
            select(ClientProfile).where(ClientProfile.client_code == client_code)
        ).scalar_one_or_none()
        
        if not client:
            return {"success": False, "error": "Client code not found"}
        
        # Get latest risk tier from ClientRiskMaster
        risk_master = db.execute(
            select(ClientRiskMaster)
            .where(ClientRiskMaster.client_id == client.id)
            .order_by(ClientRiskMaster.submitted_at.desc())
        ).first()
        
        # If not found in risk master, check client profile directly
        category_name = risk_master[0].category_name if risk_master else client.risk_profile
        
        return {
            "success": True,
            "client_name": client.client_name,
            "registration_number": client.advisor_registration_number,
            "category_name": category_name or "Not Available"
        }

    @staticmethod
    def create_allocation(
        db: Session, 
        payload: AssetAllocationCreate,
        user_ip: str,
        user_agent: str
    ) -> AssetAllocation:
        # 1. Fetch Client
        client = db.execute(
            select(ClientProfile).where(ClientProfile.client_code == payload.client_code)
        ).scalar_one_or_none()
        
        if not client:
            raise ValueError(f"Client with code {payload.client_code} not found")

        # 2. Generate System Conclusion if requested and not already provided by frontend
        system_conclusion = payload.system_conclusion
        if not system_conclusion and payload.generate_system_conclusion:
            allocation_dict = {
                'equities_percentage': payload.equities_percentage,
                'debt_securities_percentage': payload.debt_securities_percentage,
                'commodities_percentage': payload.commodities_percentage
            }
            system_conclusion = AssetAllocationService.generate_system_conclusion(
                client.client_name, payload.assigned_risk_tier, allocation_dict
            )

        # 3. Create AssetAllocation record
        allocation = AssetAllocation(
            client_id=client.id,
            ia_registration_number=payload.ia_registration_number,
            assigned_risk_tier=payload.assigned_risk_tier,
            tier_recommendation=payload.tier_recommendation,
            equities_percentage=payload.equities_percentage,
            debt_securities_percentage=payload.debt_securities_percentage,
            commodities_percentage=payload.commodities_percentage,
            stocks_percentage=payload.stocks_percentage,
            mutual_fund_equity_percentage=payload.mutual_fund_equity_percentage,
            ulip_equity_percentage=payload.ulip_equity_percentage,
            fixed_deposits_bonds_percentage=payload.fixed_deposits_bonds_percentage,
            mutual_fund_debt_percentage=payload.mutual_fund_debt_percentage,
            ulip_debt_percentage=payload.ulip_debt_percentage,
            gold_etf_percentage=payload.gold_etf_percentage,
            silver_etf_percentage=payload.silver_etf_percentage,
            system_conclusion=system_conclusion,
            generate_system_conclusion=payload.generate_system_conclusion,
            discussion_notes=payload.discussion_notes,
            disclaimer_text=payload.disclaimer_text,
            total_allocation=payload.equities_percentage + payload.debt_securities_percentage + payload.commodities_percentage
        )
        
        db.add(allocation)
        db.flush()

        # 4. Log Audit
        audit = IAMasterAuditTrail(
            action_type="ASSET_ALLOCATION_SAVE",
            table_name="asset_allocations",
            record_id=str(allocation.id),
            changes=json.dumps({
                "client_code": payload.client_code,
                "equities": payload.equities_percentage,
                "debt": payload.debt_securities_percentage,
                "commodities": payload.commodities_percentage
            }),
            user_ip=user_ip,
            user_agent=user_agent
        )
        db.add(audit)
        
        db.commit()
        return allocation

    @staticmethod
    def get_allocation_by_id(db: Session, allocation_id: uuid.UUID) -> Optional[AssetAllocation]:
        return db.execute(
            select(AssetAllocation)
            .options(joinedload(AssetAllocation.client))
            .where(AssetAllocation.id == allocation_id)
        ).scalar_one_or_none()

    @staticmethod
    def list_allocations(db: Session) -> List[dict]:
        results = db.execute(
            select(AssetAllocation, ClientProfile.client_name, ClientProfile.client_code)
            .join(ClientProfile, AssetAllocation.client_id == ClientProfile.id)
            .order_by(AssetAllocation.created_at.desc())
        ).all()
        
        output = []
        for row in results:
            allocation = row[0]
            allocation.client_name = row.client_name
            allocation.client_code = row.client_code
            output.append(allocation)
            
        return output
