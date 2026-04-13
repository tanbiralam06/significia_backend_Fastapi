import uuid
from typing import Dict, Any, List, Optional
from app.services.bridge_client import BridgeClient
from app.schemas.data_rectification_schema import RectificationCreate, RectificationResponse

class RectificationService:
    @staticmethod
    async def get_current_values(bridge: BridgeClient, module: str, record_id: str) -> Dict[str, Any]:
        """
        Fetches the current state of a record from the relevant module via the Bridge.
        """
        module = module.upper()
        
        # 1. Map module name to Bridge path
        # Note: most modules currently use clientId as the record_id for initiation
        path_map = {
            "CLIENT": f"/clients/{record_id}",
            "RISK": f"/risk-assessments/{record_id}",
            "FINANCIAL": f"/financial-analysis/profiles/{record_id}",
            "ASSET": f"/asset-allocations?client_id={record_id}"
        }
        
        path = path_map.get(module)
        if not path:
            return {}
            
        try:
            res = await bridge.get(path)
            # If Bridge returns a list (e.g. all assessments for a client), take the first/latest
            if isinstance(res, list) and len(res) > 0:
                return res[0]
            return res if isinstance(res, dict) else {}
        except Exception:
            return {}

    @staticmethod
    async def initiate_rectification(bridge: BridgeClient, payload: RectificationCreate, requested_by_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calls Bridge to create a new Data Rectification record.
        """
        data = {
            "client_id": str(payload.client_id),
            "module": payload.module,
            "record_id": str(payload.record_id),
            "current_version": payload.current_version,
            "proposed_changes": [c.model_dump() for c in payload.proposed_changes],
            "justification_details": payload.justification_details.model_dump(),
            "impact_declaration": payload.impact_declaration.model_dump(),
            "confirmation_mode": payload.confirmation_mode,
            "confirmation_reference": payload.confirmation_reference,
            "is_investor_requested": payload.is_investor_requested,
            "initiation_reason": payload.initiation_reason,
            "requested_by_id": str(requested_by_id)
        }
        return await bridge.post("/rectification/initiate", data=data)



    @staticmethod
    async def update_rectification(bridge: BridgeClient, rectification_id: uuid.UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an existing rectification record via the Bridge.
        """
        return await bridge.patch(f"/rectification/{rectification_id}", data=data)


    @staticmethod
    async def upload_signed_document(bridge: BridgeClient, rectification_id: uuid.UUID, file_bytes: bytes, filename: str, content_type: str, doc_type: str = "signed_form") -> Dict[str, Any]:
        """
        Uploads the scanned document to the Bridge and transitions status.
        """
        return await bridge.upload_file(
            f"/rectification/{rectification_id}/upload",
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            data={"doc_type": doc_type}
        )

    @staticmethod
    async def approve_rectification(bridge: BridgeClient, rectification_id: uuid.UUID) -> Dict[str, Any]:
        """
        IA Final approval via the Bridge.
        """
        return await bridge.post(f"/rectification/{rectification_id}/approve")

    @staticmethod
    async def list_rectifications(bridge: BridgeClient, client_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        """
        Lists all rectification records via the Bridge.
        """
        params = {}
        if client_id:
            params["client_id"] = str(client_id)
            
        return await bridge.get("/rectification/list", params=params)
