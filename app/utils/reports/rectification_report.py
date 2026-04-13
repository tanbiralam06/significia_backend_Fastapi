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
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*primary_black)
        pdf.cell(0, 10, "DATA CORRECTION AUTHORIZATION FORM", ln=True, align="C")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 5, "PRE-EDIT APPROVAL FOR VERSION CREATION", ln=True, align="C")
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
        draw_field("Current Version", f"v{rectification.get('current_version')}", 0)
        draw_field("Edit Serial No.", rectification.get("serial_no"), col_w)
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
        draw_field("Requested By", rectification.get("requested_by_name", "Staff / IA Employee"), 0)
        created_at = rectification.get("created_at", "")
        if isinstance(created_at, str) and "T" in created_at:
             created_at = created_at.split("T")[0]
        draw_field("Timestamp", str(created_at), col_w)

        pdf.ln(12)

        # Section 3: Purpose of Edit
        section_title(3, "Purpose of Edit")
        pdf.set_font("helvetica", "B", 8)
        modes = ["Data Correction", "Client Update", "Assumption Change", "Input Error", "Other"]
        current_mode = rectification.get("confirmation_mode", "Data Correction")
        
        pdf.set_x(15)
        for mode in modes:
            is_checked = mode in current_mode
            pdf.set_font("zapfdingbats", "", 10)
            pdf.cell(5, 5, "4" if is_checked else "o", 1, 0, 'C')
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(35, 5, f" {mode.upper()}", 0, 0)
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
            pdf.cell(40, 8, str(chg.get("field", "")).upper(), 1, 0, 'L')
            pdf.cell(45, 8, str(chg.get("current", "")), 1, 0, 'L')
            pdf.cell(45, 8, str(chg.get("proposed", "")), 1, 0, 'L')
            pdf.cell(60, 8, str(chg.get("reason", "")), 1, 1, 'L')
        pdf.ln(10)

        # Section 5: Declaration
        section_title(5, "Declaration (By Requestor)")
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(0, 5, '"I confirm that the proposed edit info is accurate and verified relative to the client\'s request or original source document. This edit was not performed prior to this authorization."', border=1)
        pdf.ln(15)
        
        pdf.line(15, pdf.get_y(), 65, pdf.get_y())
        pdf.set_font("helvetica", "B", 7)
        pdf.text(15, pdf.get_y() + 4, "STAFF SIGNATURE")
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
