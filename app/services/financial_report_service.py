import logging
import hashlib
import json
import os
from datetime import datetime
from typing import Optional, Tuple
from types import SimpleNamespace
from fastapi.responses import StreamingResponse
from app.services.bridge_client import BridgeClient
from app.utils.financial_report_generator import FinancialReportGenerator
from app.utils.file_utils import resolve_logo_to_local_path
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def get_safe(obj, key, default=None):
    """Safely get a value from either a dictionary or a SimpleNamespace."""
    if obj is None:
        return default
    if hasattr(obj, "get"):
        return obj.get(key, default)
    return getattr(obj, key, default)

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

def compute_data_fingerprint(profile_data, result_data) -> str:
    """Generates a stable SHA-256 hash of the input data used for the report."""
    payload = {
        "profile": profile_data,
        "result": result_data,
        "version": get_safe(profile_data, "version_number", 1)
    }
    # Sort keys to ensure stability
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

async def record_report_audit(
    bridge: BridgeClient,
    client_id: str,
    profile_id: str,
    report_type: str,
    version_number: int,
    data_hash: str,
    action: str = "GENERATED",
    change_summary: Optional[str] = None,
    existing_id: Optional[str] = None
) -> Optional[str]:
    """Helper to record report generation/delivery events in the Bridge."""
    try:
        payload = {
            "client_id": client_id,
            "profile_id": profile_id,
            "report_type": report_type,
            "version_number": version_number,
            "report_hash": data_hash,
            "change_summary": change_summary,
            "metadata": {"action": action, "source": "backend_proxy"}
        }
        if existing_id:
            payload["id"] = existing_id
            
        resp = await bridge.post("/reports/history", data=payload)
        return get_safe(resp, "short_id") or get_safe(resp, "id")
    except Exception as e:
        logger.warning(f"Failed to record report history: {e}")
        return None

class FinancialReportService:
    @staticmethod
    async def regenerate_report_buffer(
        bridge: BridgeClient,
        db: Session,
        profile_id: str,
        version: int,
        report_type: str = "PDF"
    ) -> Tuple[bytes, str, str, Any, Any]:
        """
        Re-generates a report buffer from original data snapshots.
        Returns: (buffer, filename, data_hash, profile_data, result_data)
        """
        # 1. Fetch original profile snapshot
        # Correct Bridge Path: /financial-analysis/profiles/id/{id}
        profile_data = await bridge.get(f"/financial-analysis/profiles/id/{profile_id}")
        if not profile_data:
            logger.error(f"Redelivery: Profile {profile_id} not found on Bridge")
            raise Exception("Profile not found")
            
        # 2. Fetch original result snapshot
        # Correct Bridge Path: /financial-analysis/results/{profile_id} (returns a list)
        results = await bridge.get(f"/financial-analysis/results/{profile_id}")
        if not results or not isinstance(results, list) or len(results) == 0:
            logger.error(f"Redelivery: Results for profile {profile_id} not found on Bridge")
            raise Exception("Results not found")
        
        # Take the most recent result
        result_data = results[0]
            
        # 3. Fetch client info
        client = await bridge.get(f"/clients/{get_safe(profile_data, 'client_id')}")
        client_name = get_safe(client, "client_name", "Valued Client")
        
        # 4. IA Metadata for Header/Footer
        ia_logo_path = None
        ia_name = None
        try:
            ia_master = await bridge.get("/ia-master")
            if ia_master:
                ia_logo_path = get_safe(ia_master, "ia_logo_path")
                ia_name = get_safe(ia_master, "ia_name") or get_safe(ia_master, "entity_name")
        except:
            pass

        resolved_logo_path = None
        if ia_logo_path:
            try:
                url_resp = await bridge.get("/storage/url", params={"key": ia_logo_path})
                if get_safe(url_resp, "url"):
                    resolved_logo_path = await resolve_logo_to_local_path(get_safe(url_resp, "url"), db)
            except Exception as e:
                logger.warning(f"Failed to resolve IA logo: {e}")

        # 5. Prepare Objects
        result_obj = dict_to_obj(result_data)
        profile_obj = dict_to_obj(profile_data)
        profile_obj.client = dict_to_obj(client)
        
        # 6. Fingerprint
        data_hash = compute_data_fingerprint(profile_data, result_data)
        
        # 7. Generate
        if report_type.upper() == "WORD":
            buffer = FinancialReportGenerator.generate_docx(
                result=result_obj,
                profile=profile_obj,
                client_name=client_name,
                ia_logo_path=resolved_logo_path or ia_logo_path,
                ia_name=ia_name,
                report_id="RE-DELIVERY", # Placeholder
                report_hash=data_hash,
                report_version=get_safe(profile_data, "version_number", 1)
            )
            ext = "docx"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            buffer = FinancialReportGenerator.generate_pdf(
                result=result_obj,
                profile=profile_obj,
                client_name=client_name,
                ia_logo_path=resolved_logo_path or ia_logo_path,
                ia_name=ia_name,
                report_id="RE-DELIVERY",
                report_hash=data_hash,
                report_version=get_safe(profile_data, "version_number", 1)
            )
            ext = "pdf"
            mime = "application/pdf"
            
        filename = f"Financial_Analysis_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.{ext}"
        return buffer, filename, data_hash, profile_data, result_data

    @staticmethod
    async def redeliver_report_via_bridge(
        bridge: BridgeClient,
        db: Session,
        audit_record: Any
    ) -> dict:
        """
        Orchestrates re-generation and email delivery via Bridge SMTP.
        """
        profile_id = get_safe(audit_record, "profile_id")
        version = get_safe(audit_record, "version_number", 1)
        client_id = get_safe(audit_record, "client_id")
        client_email = get_safe(audit_record, "client_email")
        client_name = get_safe(audit_record, "client_name", "Client")
        
        if not client_email:
            logger.warning(f"Redelivery aborted: No email found in audit record for report_id={get_safe(audit_record, 'id')}")
            return {
                "success": False, 
                "message": f"Client email missing. Please update the client's email in the master records before re-delivering."
            }

        try:
            buffer, filename, data_hash, profile_data, result_data = await FinancialReportService.regenerate_report_buffer(
                bridge, db, str(profile_id), version, "PDF"
            )
            
            # Record the delivery event in history (Using the existing record ID for direct update)
            await record_report_audit(
                bridge=bridge,
                client_id=str(client_id),
                profile_id=str(profile_id),
                report_type="financial_analysis",
                version_number=version,
                data_hash=data_hash,
                action="RE-DELIVERED",
                change_summary=f"Re-delivered report v{version} to {client_email}",
                existing_id=get_safe(audit_record, "id")
            )
            
            # Send via Bridge SMTP
            return await bridge.post_multipart(
                "/email/send",
                files={"files": (filename, buffer, "application/pdf")},
                data={
                    "recipient": client_email,
                    "recipient_name": client_name,
                    "subject": f"Financial Analysis Report — {client_name}",
                    "body": f"Dear {client_name},\n\nPlease find attached your Financial Analysis report (Re-delivered).",
                    "context_type": "profile",
                    "context_id": str(profile_id)
                }
            )
        except Exception as e:
            logger.error(f"Redelivery failed: {e}")
            return {"success": False, "message": str(e)}
