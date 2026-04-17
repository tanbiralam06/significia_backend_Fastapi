import io
import os
from datetime import datetime, date
from typing import List, Optional
from app.utils.pdf_generator import BaseReportPDF

class RectificationPDFGenerator:
    @staticmethod
    def generate_rectification_form(rectification: dict, client: dict, ia_data: Optional[dict] = None) -> bytes:
        pdf = BaseReportPDF(
            advisor_name=ia_data.get('name_of_ia') if ia_data else "Investment Adviser",
            entity_name=ia_data.get('name_of_entity') if ia_data else None,
            ia_reg_no=ia_data.get('ia_registration_number') if ia_data else None
        )
        pdf.add_page()
        
        # Color Palette
        primary_black = (10, 10, 10)
        accent_grey = (245, 245, 245)
        text_muted = (100, 100, 100)
        
        # Header
        is_deactivation = rectification.get("module") == "DEACTIVATION"
        main_title = "CLIENT DEACTIVATION AUTHORIZATION FORM" if is_deactivation else "DATA CORRECTION AUTHORIZATION FORM"
        sub_title = "PERMANENT TERMINATION OF SERVICE AUTHORIZATION" if is_deactivation else "PRE-EDIT APPROVAL FOR VERSION CREATION"

        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*primary_black)
        pdf.cell(0, 10, main_title, ln=True, align="C")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 5, sub_title, ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

        def section_title(num, title):
            pdf.set_fill_color(*accent_grey)
            pdf.rect(10, pdf.get_y(), 190, 10, 'F')
            pdf.set_draw_color(0, 0, 0)
            pdf.line(10, pdf.get_y(), 10, pdf.get_y() + 10) # Left border thick
            
            pdf.set_xy(15, pdf.get_y() + 2)
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(0, 0, 0)
            pdf.cell(6, 6, str(num), 0, 0, 'C', fill=True)
            
            pdf.set_x(25)
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(*primary_black)
            pdf.cell(0, 6, title.upper(), 0, 1)
            pdf.ln(5)

        # Section 1: Basic Identification
        section_title(1, "Basic Identification")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*text_muted)
        
        col_w = 63
        start_y = pdf.get_y()
        
        def draw_field(label, value, x_offset):
            pdf.set_xy(10 + x_offset, start_y)
            pdf.set_font("helvetica", "B", 7)
            pdf.set_text_color(*text_muted)
            pdf.cell(col_w, 4, label.upper(), 0, 1)
            pdf.set_x(10 + x_offset)
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(*primary_black)
            pdf.cell(col_w, 6, str(value or "N/A"), 0, 1)
            pdf.line(10 + x_offset, pdf.get_y(), 10 + x_offset + 55, pdf.get_y())

        draw_field("Client Name", client.get("client_name"), 0)
        draw_field("Client Code", client.get("client_code"), col_w)
        draw_field("Module / Program", rectification.get("module"), col_w * 2)
        pdf.ln(5)
        
        start_y = pdf.get_y()
        if rectification.get("module") != "CLIENT":
            draw_field("Current Version", f"v{rectification.get('current_version')}", 0)
            draw_field("Edit Serial No.", rectification.get("serial_no"), col_w)
        else:
            draw_field("Edit Serial No.", rectification.get("serial_no"), 0)
        pdf.ln(12)
        
        # Initiation Reason (New)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 4, "INITIATION REASON", ln=True)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(*primary_black)
        pdf.multi_cell(0, 5, f"\"{rectification.get('initiation_reason', 'N/A')}\"", border='B')
        pdf.ln(5)


        # Section 2: Request Details
        section_title(2, "Request Details")
        start_y = pdf.get_y()
        requested_name = rectification.get("requested_by_name", "Staff / IA Employee")
        requested_role = rectification.get("requested_by_role")
        display_requested = f"{requested_name} ({requested_role.upper()})" if requested_role else requested_name
        draw_field("Requested By", display_requested, 0)
        
        created_at_raw = rectification.get("created_at", "")
        formatted_ts = str(created_at_raw)
        
        try:
            from datetime import datetime, timedelta
            if isinstance(created_at_raw, str):
                # Handle ISO format from bridge (usually UTC)
                ts_obj = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                # Localize to IST for the report (matching the UI)
                ts_obj = ts_obj + timedelta(hours=5, minutes=30)
                formatted_ts = ts_obj.strftime("%B %d, %Y %I:%M %p")
            elif isinstance(created_at_raw, datetime):
                # If already a datetime, assume it needs offset if it's UTC
                ts_obj = created_at_raw + timedelta(hours=5, minutes=30)
                formatted_ts = ts_obj.strftime("%B %d, %Y %I:%M %p")
        except Exception:
            pass

        draw_field("Timestamp", formatted_ts, col_w)

        pdf.ln(12)

        # Section 3: Purpose of Edit
        section_title(3, "Purpose of Edit")
        pdf.set_font("helvetica", "B", 8)
        modes = ["Data Correction", "Client Update", "Assumption Change", "Input Error", "Other"]
        
        # Robust selection detection for comma-separated strings
        purpose_str = rectification.get("purpose_of_edit", "")
        selected_modes = [m.strip().upper() for m in (purpose_str.split(",") if isinstance(purpose_str, str) else [])]
        
        pdf.set_x(15)
        for mode in modes:
            is_checked = mode.upper() in selected_modes
            
            # Draw standard box with Tick using ZapfDingbats
            pdf.set_font("zapfdingbats", "", 10)
            pdf.cell(5, 5, "4" if is_checked else "", 1, 0, 'C')
            
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(33, 5, f" {mode.upper()}", 0, 0)
        pdf.ln(12)

        # Section 4: Proposed Changes
        section_title(4, "Proposed Changes")
        changes = rectification.get("proposed_changes", [])
        
        # Table Header
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(40, 8, "FIELD NAME", 1, 0, 'L', fill=True)
        pdf.cell(45, 8, "CURRENT VALUE", 1, 0, 'L', fill=True)
        pdf.cell(45, 8, "PROPOSED VALUE", 1, 0, 'L', fill=True)
        pdf.cell(60, 8, "REASON", 1, 1, 'L', fill=True)
        
        pdf.set_font("helvetica", "", 8)
        if not changes:
            pdf.cell(190, 10, "No fields selected for correction", 1, 1, 'C')
        
        for chg in changes:
            field = str(chg.get("field", "")).upper()
            curr = str(chg.get("current", ""))
            prop = str(chg.get("proposed", ""))
            reas = str(chg.get("reason", ""))
            
            # Calculate dynamic height based on text wrapping
            h_unit = 4.5
            l_f = pdf.multi_cell(40, h_unit, field, split_only=True)
            l_c = pdf.multi_cell(45, h_unit, curr, split_only=True)
            l_p = pdf.multi_cell(45, h_unit, prop, split_only=True)
            l_r = pdf.multi_cell(60, h_unit, reas, split_only=True)
            
            row_h = max(len(l_f), len(l_c), len(l_p), len(l_r), 1) * h_unit
            if row_h < 8: row_h = 8 # Stick to minimum original height
            
            # Check for page break
            if pdf.get_y() + row_h > 270:
                pdf.add_page()
            
            cur_x, cur_y = pdf.get_x(), pdf.get_y()
            
            # Draw Cell Borders (Rectangles for consistent row height)
            pdf.rect(cur_x, cur_y, 40, row_h)
            pdf.rect(cur_x+40, cur_y, 45, row_h)
            pdf.rect(cur_x+85, cur_y, 45, row_h)
            pdf.rect(cur_x+130, cur_y, 60, row_h)
            
            # Render Wrapped Text
            pdf.multi_cell(40, h_unit, field, align='L')
            pdf.set_xy(cur_x + 40, cur_y)
            pdf.multi_cell(45, h_unit, curr, align='L')
            pdf.set_xy(cur_x + 85, cur_y)
            pdf.multi_cell(45, h_unit, prop, align='L')
            pdf.set_xy(cur_x + 130, cur_y)
            pdf.multi_cell(60, h_unit, reas, align='L')
            
            pdf.set_y(cur_y + row_h)
        pdf.ln(10)

        # Section 5: Detailed Justification
        section_title(5, "Detailed Justification")
        just = rectification.get("justification_details", {})
        
        def draw_justification(label, text_val):
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(*text_muted)
            pdf.cell(0, 5, label, ln=True)
            pdf.set_font("helvetica", "", 9)
            pdf.set_text_color(*primary_black)
            pdf.multi_cell(0, 5, str(text_val or "---"), border='B')
            pdf.ln(4)

        draw_justification("1. What is incorrect in current data?", just.get("q1"))
        draw_justification("2. Why is change required?", just.get("q2"))
        draw_justification("3. Source of revised data?", just.get("q3"))
        pdf.ln(5)

        # Section 6: Client Confirmation
        section_title(6, "Client Confirmation (If Available)")
        pdf.set_font("helvetica", "B", 8)
        conf_modes = ["Written/Email", "Verbal", "Not applicable"]
        
        conf_mode_str = rectification.get("confirmation_mode", "")
        selected_conf_modes = [m.strip().upper() for m in (conf_mode_str.split(",") if isinstance(conf_mode_str, str) else [])]
        
        pdf.set_x(15)
        for mode in conf_modes:
            is_checked = mode.upper() in selected_conf_modes
            pdf.set_font("zapfdingbats", "", 10)
            pdf.cell(5, 5, "4" if is_checked else "", 1, 0, 'C')
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(45, 5, f" {mode.upper()}", 0, 0)
        pdf.ln(8)
        
        pdf.set_x(15)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(*text_muted)
        pdf.cell(20, 5, "REFERENCE:", 0, 0)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*primary_black)
        pdf.cell(0, 5, str(rectification.get("confirmation_reference", "N/A")), border='B', ln=True)
        pdf.ln(10)

        # Section 7: Impact Declaration
        section_title(7, "Impact Declaration")
        impact = rectification.get("impact_declaration", {})
        
        pdf.set_font("helvetica", "B", 8)
        
        # Grid layout for checkboxes
        fields = [
            ("financial", "IMPACTS FINANCIAL ANALYSIS"),
            ("risk", "IMPACTS RISK PROFILE"),
            ("asset_allocation", "IMPACTS ASSET ALLOCATION"),
            ("portfolio", "IMPACTS PORTFOLIO / HOLDINGS"),
            ("product_basket", "IMPACTS PRODUCT BASKET"),
            ("target_portfolio", "IMPACTS TARGET PORTFOLIO"),
            ("other", "OTHERS")
        ]
        
        row_count = 0
        for i, (key, label) in enumerate(fields):
            if i % 2 == 0:
                pdf.set_x(15)
            
            is_checked = impact.get(key)
            pdf.set_font("zapfdingbats", "", 10)
            pdf.cell(5, 5, "4" if is_checked else "o", 1, 0, 'C')
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(60, 5, f" {label}", 0, 0)
            
            if i % 2 != 0 or i == len(fields) - 1:
                pdf.ln(7)
                row_count += 1
        
        # Other Details if "Other" is checked
        if impact.get("other"):
            pdf.ln(2)
            pdf.set_x(15)
            pdf.set_font("helvetica", "B", 7)
            pdf.set_text_color(*text_muted)
            pdf.cell(0, 4, "OTHER IMPACT DETAILS", ln=True)
            pdf.set_font("helvetica", "", 9)
            pdf.set_text_color(*primary_black)
            pdf.multi_cell(0, 5, impact.get("other_details") or "---", border='B')
            pdf.ln(2)

        pdf.ln(2)
        pdf.set_x(15)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 4, "REMARKS / MITIGATION", ln=True)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(*primary_black)
        pdf.multi_cell(0, 5, impact.get("remarks") or "", border='B')
        pdf.ln(10)

        # Section 8: Declaration
        section_title(8, "Declaration (By Requestor)")
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(0, 5, '"I confirm that the proposed edit info is accurate and verified relative to the client\'s request or original source document. This edit was not performed prior to this authorization."', border=1)
        pdf.ln(15)
        
        cur_y = pdf.get_y()
        pdf.line(15, cur_y, 65, cur_y)
        pdf.set_font("helvetica", "B", 7)
        pdf.text(15, cur_y + 4, "STAFF SIGNATURE")
        
        # Add Requested On Date matching the UI
        try:
            from datetime import datetime, timedelta
            raw_ts = rectification.get("created_at", "")
            if isinstance(raw_ts, str):
                ts_obj = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                # Re-localize to IST for correct date flipping
                ts_obj = ts_obj + timedelta(hours=5, minutes=30)
                req_date = ts_obj.strftime("%d/%m/%Y")
            else:
                req_date = str(raw_ts).split("T")[0]
            
            if req_date:
                pdf.set_font("helvetica", "B", 7)
                pdf.set_text_color(*text_muted)
                pdf.text(140, cur_y, "REQUESTED ON")
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*primary_black)
                pdf.text(140, cur_y + 4, req_date)
        except Exception:
            pass
            
        pdf.ln(15)

        # Section 6: IA Authorization
        if pdf.get_y() > 230:
            pdf.add_page()
            
        pdf.set_fill_color(250, 250, 250)
        pdf.rect(10, pdf.get_y(), 190, 40, 'F')
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.4)
        pdf.rect(10, pdf.get_y(), 190, 40, 'D')
        
        pdf.set_xy(15, pdf.get_y() + 5)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 5, "9  IA AUTHORIZATION CASE", ln=True)
        pdf.set_font("helvetica", "B", 8)
        pdf.ln(2)
        
        is_approved = bool(rectification.get("approved_by_id"))
        pdf.set_font("zapfdingbats", "", 12)
        pdf.set_x(15)
        pdf.cell(6, 6, "4" if is_approved else "o", 1, 0, 'C')
        pdf.set_font("helvetica", "B", 7)
        pdf.multi_cell(170, 4, " I, THE INVESTMENT ADVISER, HAVE REVIEWED THE JUSTIFICATION AND UPLOADED EVIDENCE, AND HEREBY AUTHORIZE THIS DATA RECTIFICATION UNDER THE STATED SERIAL NO.")
        
        pdf.ln(5)
        pdf.set_x(15)
        pdf.line(15, pdf.get_y() + 10, 65, pdf.get_y() + 10)
        pdf.text(15, pdf.get_y() + 14, "IA PHYSICAL SIGNATURE")
        
        pdf.set_xy(130, pdf.get_y() + 2)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(60, 5, "IA SIGNED" if is_approved else "PENDING...", 0, 1, 'R')
        pdf.set_font("helvetica", "B", 7)
        pdf.set_x(130)
        pdf.cell(60, 5, "AUTHORIZED BY (DIGITAL)", 0, 1, 'R')

        # Footer
        pdf.set_y(-25)
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 5, f"SERIAL AUTH: {rectification.get('serial_no')}", 0, 0, 'R')
        
        return bytes(pdf.output())
