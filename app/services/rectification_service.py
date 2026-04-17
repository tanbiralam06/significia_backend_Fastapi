import uuid
from typing import Dict, Any, List, Optional
from app.services.bridge_client import BridgeClient
from app.schemas.data_rectification_schema import RectificationCreate, RectificationResponse

# Fields that are outcomes of formal assessment processes and MUST NOT be rectified
# via the data rectification workflow. These are managed through their own assessment flows.
NON_RECTIFIABLE_FIELDS = {
    "CLIENT": [
        # ── System / Auth fields ──────────────────────────────────────────
        "id",
        "user_id",
        "role",
        "password",
        "tenant_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "is_active",
        "status",

        # ── Document / File paths (system-managed) ────────────────────────
        "documents",
        "financial_analysis_path",
        "other_document_path",
        "agreement_copy_path",

        # ── Core Identity (immutable after onboarding) ────────────────────
        "client_name",
        "name",
        "client_code",
        "pan_number",
        "aadhar_number",
        "passport_number",
        "date_of_birth",

        # ── KYC / Compliance audit fields ─────────────────────────────────
        "kyc_verified",
        "ckyc_number",

        # ── IPV fields ────────────────────────────────────────────────────
        "ipv_done_by_id",
        "ipv_date",

        # ── Advisor / IA fields ───────────────────────────────────────────
        "advisor_name",
        "advisor_registration_number",

        # ── Agreement / Registration dates ────────────────────────────────
        "client_date",
        "agreement_date",

        # ── Rectification audit trail ─────────────────────────────────────
        "rectification_serial_no",

        # ── Assessment outcome fields (managed via their own modules) ─────
        "risk_profile",
        "investment_experience",
        "investment_horizon",
        "liquidity_needs",
        "investment_objectives",
    ]
}

class RectificationService:
    @staticmethod
    async def get_current_values(bridge: BridgeClient, module: str, record_id: str) -> Dict[str, Any]:
        """
        Fetches the current state of a CLIENT record from the Bridge for rectification.
        Only CLIENT module is supported for data rectification.
        Financial Analysis, Risk Profile, and Asset Allocation are NOT rectifiable.
        """
        module = module.upper()
        
        if module not in ["CLIENT", "DEACTIVATION"]:
            return {}
        
        try:
            res = await bridge.get(f"/clients/{record_id}")
            if not isinstance(res, dict):
                return {}
            # Strip out non-rectifiable fields before returning
            non_rectifiable = NON_RECTIFIABLE_FIELDS.get("CLIENT", [])
            # For DEACTIVATION, we specifically allow 'is_active' even if it's in blacklist
            filtered = {k: v for k, v in res.items() if k not in non_rectifiable}
            if module == "DEACTIVATION":
                filtered["is_active"] = res.get("is_active", True)
            return filtered
        except Exception:
            return {}

    @staticmethod
    async def initiate_rectification(bridge: BridgeClient, payload: RectificationCreate, requested_by_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calls Bridge to create a new Data Rectification record.
        Only CLIENT and DEACTIVATION modules are permitted.
        """
        module = payload.module.upper()
        if module not in ["CLIENT", "DEACTIVATION"]:
            raise ValueError(
                f"Data Rectification is restricted to Client Master Data and Deactivation. "
                f"Module '{payload.module}' cannot be rectified through this workflow."
            )
        # --- COMPLIANCE GUARD: Block rectifications for deactivated clients ---
        try:
            client_data = await bridge.get(f"/clients/{payload.client_id}")
            if not client_data.get("is_active", True):
                raise HTTPException(
                    status_code=400,
                    detail="Compliance Error: This client is deactivated. No further data rectifications or status changes are permitted for terminated accounts."
                )
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(404, detail="Client not found in Bridge database.")
            raise

        data = {
            "client_id": str(payload.client_id),
            "module": payload.module,
            "record_id": str(payload.record_id),
            "current_version": payload.current_version,
            "proposed_changes": [c.model_dump() for c in payload.proposed_changes],
            "justification_details": payload.justification_details.model_dump(),
            "impact_declaration": payload.impact_declaration.model_dump(),
            "purpose_of_edit": payload.purpose_of_edit,
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
    async def list_rectifications(
        bridge: BridgeClient, 
        client_id: Optional[uuid.UUID] = None,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lists rectification records via the Bridge with pagination and search.
        """
        params = {
            "limit": limit,
            "offset": (page - 1) * limit
        }
        if client_id:
            params["client_id"] = str(client_id)
        if search:
            params["search"] = search
            
        return await bridge.get("/rectification/list", params=params)
