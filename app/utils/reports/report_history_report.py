"""
Report History Report Generator
───────────────────────────────
Generates logs of generated reports in CSV and JSON formats.
Used for SEBI compliance audit and record-keeping of generated deliverables.
"""

import io
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional


class ReportHistoryReportGenerator:
    """
    Converts report history entries into exportable CSV or JSON format.
    """

    # CSV column order and display headers
    CSV_COLUMNS = [
        ("created_at", "Timestamp"),
        ("short_id", "Audit ID"),
        ("version_number", "Version"),
        ("report_type_label", "Report Type"),
        ("client_name", "Client Name"),
        ("client_code", "Client Code"),
        ("file_format", "Format"),
        ("report_hash", "Integrity Hash (SHA-256)"),
        ("change_summary", "Change Summary"),
        ("delivery_status", "Delivery Status"),
        ("delivered_at", "Delivered At"),
        # Technical IDs
        ("id", "Report ID"),
        ("client_id", "Client ID"),
    ]

    @staticmethod
    def _get_report_type_label(report_type: str) -> str:
        """Helper to format report types into human-readable labels."""
        mapping = {
            "risk_assessment": "Risk Assessment",
            "asset_allocation": "Asset Allocation",
            "financial_analysis": "Financial Analysis",
            "ia_master": "IA Master",
        }
        return mapping.get(report_type.lower(), report_type.replace("_", " ").capitalize())

    @staticmethod
    def _format_timestamp(ts_str: str) -> str:
        """Parse ISO timestamp and format for readable report."""
        if not ts_str:
            return ""
        try:
            # Handle ISO format (from Bridge)
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except Exception:
            return ts_str

    @staticmethod
    def generate_csv(
        entries: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        ia_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate a CSV report history log.
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # ── Metadata Header Rows ────────────────────────────────────
        writer.writerow(["REPORT GENERATION HISTORY LOG"])
        writer.writerow([""])

        # IA Identity block
        if ia_data:
            writer.writerow(["Entity Name", ia_data.get("name_of_entity", "")])
            writer.writerow(["IA Name", ia_data.get("name_of_ia", "")])
            writer.writerow(["Registration No", ia_data.get("ia_registration_number", "")])
        
        writer.writerow([""])

        # Date range / filters
        if filters:
            from_date = filters.get("from_date") or "All Time"
            to_date = filters.get("to_date") or "Present"
            writer.writerow(["Report Period", f"{from_date} to {to_date}"])
            if filters.get("report_type"):
                writer.writerow(["Filtered Type", ReportHistoryReportGenerator._get_report_type_label(filters["report_type"])])
        else:
            writer.writerow(["Report Period", "All Time"])

        exported_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S IST")
        writer.writerow(["Exported At", exported_at])
        writer.writerow(["Total Reports", str(len(entries))])
        writer.writerow([""])

        # ── Column Headers ──────────────────────────────────────────
        headers = [col[1] for col in ReportHistoryReportGenerator.CSV_COLUMNS]
        writer.writerow(headers)

        # ── Data Rows ───────────────────────────────────────────────
        for entry in entries:
            # Inject helper labels
            entry["report_type_label"] = ReportHistoryReportGenerator._get_report_type_label(entry.get("report_type", ""))
            entry["delivery_status"] = "Delivered" if entry.get("is_delivered") else "Pending"
            if not entry.get("short_id"):
                entry["short_id"] = str(entry.get("id", ""))[:8]
            
            # Format timestamps
            display_ts = ReportHistoryReportGenerator._format_timestamp(entry.get("created_at", ""))
            delivered_ts = ReportHistoryReportGenerator._format_timestamp(entry.get("delivered_at", "")) if entry.get("delivered_at") else ""

            row = []
            for col_key, _ in ReportHistoryReportGenerator.CSV_COLUMNS:
                if col_key == "created_at":
                    row.append(display_ts)
                elif col_key == "delivered_at":
                    row.append(delivered_ts)
                else:
                    val = entry.get(col_key, "")
                    if val is None:
                        val = ""
                    row.append(str(val))
            writer.writerow(row)

        csv_content = output.getvalue()
        return ("\ufeff" + csv_content).encode("utf-8")

    @staticmethod
    def generate_json(
        entries: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        ia_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate a JSON report history log.
        """
        exported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")

        report = {
            "report_type": "REPORT_HISTORY_EXPORT",
            "report_title": "Report Generation History Log",
            "metadata": {
                "exported_at": exported_at,
                "total_entries": len(entries),
                "filters": filters or {},
            },
        }

        if ia_data:
            report["ia_identity"] = {
                "entity_name": ia_data.get("name_of_entity", ""),
                "ia_name": ia_data.get("name_of_ia", ""),
                "registration_number": ia_data.get("ia_registration_number", ""),
            }

        clean_entries = []
        for entry in entries:
            entry["report_type_label"] = ReportHistoryReportGenerator._get_report_type_label(entry.get("report_type", ""))
            
            clean = {}
            for key, val in entry.items():
                if isinstance(val, datetime):
                    clean[key] = val.isoformat()
                elif val is None:
                    clean[key] = None
                else:
                    clean[key] = val
            clean_entries.append(clean)

        report["entries"] = clean_entries
        return json.dumps(report, indent=2, ensure_ascii=False, default=str).encode("utf-8")

    @staticmethod
    def get_filename(format: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> str:
        """Generate a descriptive filename for the export."""
        date_suffix = datetime.now().strftime("%Y%m%d")
        period = "all_time"
        if from_date and to_date:
            period = f"{from_date}_to_{to_date}"
        elif from_date:
            period = f"from_{from_date}"
        elif to_date:
            period = f"until_{to_date}"

        return f"Report_History_{period}_{date_suffix}.{format}"
