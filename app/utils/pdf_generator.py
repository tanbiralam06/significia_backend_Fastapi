import io
import os
from datetime import datetime, date
from fpdf import FPDF
from typing import List, Optional
from app.constants import REQUIRED_DOCUMENTS

class BaseReportPDF(FPDF):
    def __init__(self, *args, **kwargs):
        self.advisor_name = kwargs.pop('advisor_name', "")
        self.entity_name = kwargs.pop('entity_name', "")
        self.ia_reg_no = kwargs.pop('ia_reg_no', "")
        self.header_text = kwargs.pop('header_text', "Internal system report - not for client communication")
        self.version = kwargs.pop('version', "")
        self.last_updated = kwargs.pop('last_updated', "")
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

    def header(self):
        # Only show header on pages after the cover page (Page 1)
        if self.page_no() > 1:
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            
            # Left side: Version and Update Date
            header_left = []
            if self.version:
                header_left.append(f"Version: {self.version}")
            if self.last_updated:
                header_left.append(f"Data Updated: {self.last_updated}")
            
            if header_left:
                self.set_x(10)
                self.cell(100, 5, " | ".join(header_left), 0, 0, 'L')
            
            # Right side disclaimer
            self.set_x(100)
            self.cell(100, 5, self.header_text, 0, 1, 'R')
            # Add a small buffer after the header
            self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('helvetica', 'I', 7)
        self.set_text_color(128, 128, 128)
        
        # Footer text: Prepared by, Entity, Reg No
        footer_parts = []
        if self.advisor_name: footer_parts.append(f"Prepared by: {self.advisor_name}")
        if self.entity_name: footer_parts.append(f"Entity: {self.entity_name}")
        if self.ia_reg_no: footer_parts.append(f"Reg No: {self.ia_reg_no}")
        footer_text = " , ".join(footer_parts)
        
        # Determine width for footer text based on orientation
        # Use getattr for compatibility between fpdf and fpdf2
        orientation = getattr(self, 'cur_orientation', getattr(self, 'orientation', 'P'))
        w = 230 if orientation == 'L' else 150
        
        # Left side
        self.cell(w, 10, footer_text, 0, 0, 'L')
        
        # Page number on the right
        self.cell(0, 10, f'Page {self.page_no()} / {{nb}}', 0, 0, 'R')

class IAPDFGenerator:
    @staticmethod
    def render_ia_cover_page(pdf, ia_data: dict, logo_path: Optional[str] = None, last_updated_str: str = "N/A"):
        pdf.add_page()
        # Colors (Premium Navy and Silver/Grey)
        primary_navy = (0, 31, 63)
        accent_blue = (0, 123, 255)
        text_dark = (33, 37, 41)
        
        # Draw elegant border
        pdf.set_draw_color(*primary_navy)
        pdf.set_line_width(0.8)
        pdf.rect(5, 5, 200, 287)
        pdf.set_line_width(0.2)
        
        # Logo Section
        pdf.set_y(50)
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, 80, pdf.get_y(), 50)
            pdf.set_y(pdf.get_y() + 60)
        else:
            pdf.ln(60)

        # Entity Name
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*primary_navy)
        name = (ia_data.get('name_of_entity') or ia_data.get('name_of_ia') or "").upper()
        pdf.cell(0, 10, name, ln=True, align="C")
        
        # Report Title
        pdf.ln(30)
        pdf.set_font("helvetica", "B", 26)
        pdf.set_text_color(*accent_blue)
        pdf.cell(0, 15, "INVESTMENT ADVISOR MASTER REPORT", ln=True, align="C")
        
        # Simple stylish separator
        pdf.set_fill_color(*accent_blue)
        pdf.set_xy(75, pdf.get_y() + 2)
        pdf.cell(60, 1.2, "", ln=True, fill=True)
        
        # Registration Info
        pdf.ln(50)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(*text_dark)
        reg_no = ia_data.get('ia_registration_number', 'N/A')
        pdf.cell(0, 10, f"SEBI REGISTRATION NO: {reg_no}", ln=True, align="C")
        
        # Footer
        pdf.set_y(260)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(120, 120, 120)
        current_date = datetime.now().strftime('%d %B %Y')
        
        # Pull lifecycle info for the cover
        version = ia_data.get('version_number', 1)
        
        pdf.cell(0, 6, f"Data Version: {version} | Last Modified: {last_updated_str}", ln=True, align="C")
        pdf.cell(0, 6, f"Report Generated for Internal System Record on: {current_date}", ln=True, align="C")
        pdf.set_text_color(200, 0, 0) # Subtle warning color for "No External Use"
        pdf.cell(0, 6, "CONFIDENTIAL - INTERNAL SYSTEM RECORD - NOT FOR EXTERNAL USE", ln=True, align="C")

    @staticmethod
    def generate_ia_report(ia_data: dict, employees: List[dict], logo_path: Optional[str] = None) -> bytes:
        # Extract version and formatted update time
        version = ia_data.get('version_number', 1)
        updated_at = ia_data.get('updated_at')
        last_updated_str = "N/A"
        
        if updated_at:
            try:
                if isinstance(updated_at, str):
                    # Handle potential 'Z' or offset strings
                    clean_ts = updated_at.split('.')[0].replace('Z', '')
                    dt = datetime.fromisoformat(clean_ts)
                    last_updated_str = dt.strftime('%d %b %Y, %I:%M %p')
                elif hasattr(updated_at, 'strftime'):
                    last_updated_str = updated_at.strftime('%d %b %Y, %I:%M %p')
            except Exception:
                last_updated_str = str(updated_at)

        pdf = BaseReportPDF(
            advisor_name=ia_data.get('name_of_ia', ''),
            entity_name=ia_data.get('name_of_entity', ''),
            ia_reg_no=ia_data.get('ia_registration_number', ''),
            header_text="Internal system record - not for external use",
            version=str(version),
            last_updated=last_updated_str
        )
        
        # 1. Render Premium Cover Page
        IAPDFGenerator.render_ia_cover_page(pdf, ia_data, logo_path, last_updated_str=last_updated_str)
        
        pdf.add_page()
        margin = 10
        primary_blue = (0, 123, 255)
        text_dark = (33, 37, 41)
        bg_grey = (248, 249, 250)
        border_grey = (210, 215, 220)

        def section_header(title):
            pdf.set_font("helvetica", "B", 13)
            pdf.set_text_color(*primary_blue)
            pdf.cell(0, 10, title, ln=True)
            pdf.ln(2)

        def render_grid_section(title, fields):
            if not fields: return
            
            pdf.set_font("helvetica", "B", 13)
            pdf.set_text_color(*primary_blue)
            pdf.cell(0, 12, title, ln=True)
            pdf.ln(2)
            
            # Draw a subtle background for the entire section
            start_y = pdf.get_y()
            
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(80, 80, 80)
            
            for i in range(0, len(fields), 2):
                pdf.set_x(margin)
                f1_label, f1_val = fields[i]
                
                # Left Column
                pdf.set_font("helvetica", "B", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(40, 9, f" {f1_label}", border='LTB', fill=False)
                pdf.set_font("helvetica", "", 10)
                pdf.set_text_color(0, 0, 0) # Solid black
                pdf.cell(55, 9, f" {f1_val or 'N/A'}", border='RTB', fill=False)
                
                # Right Column
                if i + 1 < len(fields):
                    f2_label, f2_val = fields[i+1]
                    pdf.set_x(margin + 95 + 5) # Small gap
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(40, 9, f" {f2_label}", border='LTB', fill=False)
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(0, 0, 0) # Solid black
                    pdf.cell(55, 9, f" {f2_val or 'N/A'}", border='RTB', fill=False)
                
                pdf.ln(12)

        # Identity Grid
        profile_fields = [
            ("Name of IA", ia_data.get('name_of_ia')),
            ("Nature of Entity", str(ia_data.get('nature_of_entity', '')).capitalize()),
            ("Entity Name", ia_data.get('name_of_entity')),
            ("Reg Number", ia_data.get('ia_registration_number')),
            ("Reg Date", str(ia_data.get('date_of_registration', 'N/A'))),
            ("Expiry Date", str(ia_data.get('date_of_registration_expiry', 'N/A'))),
            ("Email ID", ia_data.get('registered_email_id')),
            ("Phone No.", ia_data.get('registered_contact_number')),
            ("CIN Number", ia_data.get('cin_number') or "N/A"),
            ("BASL ID", ia_data.get('basl_membership_id') or "N/A")
        ]
        render_grid_section("IA Entity Profile", profile_fields)
        
        # Address (Full Width)
        pdf.set_x(margin)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(40, 9, " Registered Address", border='LTB')
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*text_dark)
        pdf.multi_cell(0, 9, f" {ia_data.get('registered_address', 'N/A')}", border='RTB')
        
        pdf.ln(10)
        
        # Bank Grid
        bank_fields = [
            ("Bank Name", ia_data.get('bank_name')),
            ("Branch", ia_data.get('bank_branch')),
            ("A/C Number", ia_data.get('bank_account_number')),
            ("IFSC Code", ia_data.get('ifsc_code'))
        ]
        render_grid_section("Nodal / Operational Bank Details", bank_fields)
        
        if employees:
            pdf.ln(5)
            
            # Helper to get name from multiple possible fields
            def get_person_name(p):
                return p.get('name') or p.get('name_of_employee') or p.get('full_name') or "N/A"

            # Categorize team members
            partners = [e for e in employees if e.get('role') in ['partner', 'owner']]
            other_staff = [e for e in employees if e.get('role') not in ['partner', 'owner']]

            # 1. Partners / Key Personnel Section
            if partners:
                section_header("Partners / Key Personnel")
                pdf.set_fill_color(240, 245, 255) # Light blue fill
                pdf.set_font("helvetica", "B", 9)
                pdf.set_text_color(0, 0, 0) # Solid black headers
                pdf.cell(50, 10, "Name", 1, 0, 'C', fill=True)
                pdf.cell(50, 10, "Designation", 1, 0, 'C', fill=True)
                pdf.cell(40, 10, "IA Reg No", 1, 0, 'C', fill=True)
                pdf.cell(50, 10, "Expiry Date", 1, 1, 'C', fill=True)
                
                pdf.set_font("helvetica", "", 9)
                pdf.set_text_color(20, 20, 20) # Deep black for row data
                for p in partners:
                    name = str(get_person_name(p))[:25]
                    designation = str(p.get('designation', 'Partner'))[:25]
                    reg_no = str(p.get('ia_registration_number', 'N/A'))
                    expiry = str(p.get('date_of_registration_expiry', 'N/A'))
                    
                    pdf.cell(50, 10, name, 1, 0, 'L')
                    pdf.cell(50, 10, designation, 1, 0, 'L')
                    pdf.cell(40, 10, reg_no, 1, 0, 'C')
                    pdf.cell(50, 10, expiry, 1, 1, 'C')
                pdf.ln(10)

            # 2. Other Registered Professionals Section
            if other_staff:
                section_header("Registered Professionals (Employees)")
                pdf.set_fill_color(248, 249, 250)
                pdf.set_font("helvetica", "B", 9)
                pdf.set_text_color(0, 0, 0) # Solid black headers
                pdf.cell(50, 10, "Name", 1, 0, 'C', fill=True)
                pdf.cell(50, 10, "Designation", 1, 0, 'C', fill=True)
                pdf.cell(40, 10, "IA Reg No", 1, 0, 'C', fill=True)
                pdf.cell(50, 10, "Expiry Date", 1, 1, 'C', fill=True)
                
                pdf.set_font("helvetica", "", 9)
                pdf.set_text_color(20, 20, 20) # Deep black for row data
                for emp in other_staff:
                    name = str(get_person_name(emp))[:25]
                    designation = str(emp.get('designation', 'Staff'))[:25]
                    reg_no = str(emp.get('ia_registration_number', 'N/A'))
                    expiry = str(emp.get('date_of_registration_expiry', 'N/A'))
                    
                    pdf.cell(50, 10, name, 1, 0, 'L')
                    pdf.cell(50, 10, designation, 1, 0, 'L')
                    pdf.cell(40, 10, reg_no, 1, 0, 'C')
                    pdf.cell(50, 10, expiry, 1, 1, 'C')

            # Add System Disclaimer at the bottom
            pdf.ln(10)
            pdf.set_font("helvetica", "I", 8)
            pdf.set_text_color(150, 150, 150)
            disclaimer = (
                "This report is generated for internal record and reference purpose only. "
                "Information contain in this report based on recorded data and is not intended for advisory or decision-making purposes. "
                "All information is based on data provided and recorded by the investment advisor and has not been independently verified by the system"
            )
            pdf.multi_cell(0, 5, disclaimer, 0, 'C')

        return bytes(pdf.output())

class ClientPDFGenerator:
    @staticmethod
    def _fmt_dt(dt_str: Optional[str]) -> str:
        if not dt_str or dt_str == "unknown":
            return "N/A"
        try:
            # Handle ISO format from Bridge
            if 'T' in dt_str:
                dt_obj = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt_obj.strftime('%d-%m-%Y %H:%M')
            return dt_str
        except:
            return dt_str

    @staticmethod
    def render_client_cover_page(pdf, client_data: dict, ia_data: dict, logo_path: Optional[str] = None, version_info: Optional[dict] = None):
        pdf.add_page()
        
        # Colors & Settings
        primary_blue = (0, 70, 160)
        text_black = (20, 20, 20)
        margin = 10
        
        # Draw a full page border for premium feel
        pdf.set_draw_color(*primary_blue)
        pdf.set_line_width(0.5)
        pdf.rect(5, 5, 200, 287)
        pdf.set_line_width(0.2)
        
        # 1. Render Archival Banner at the VERY TOP of the cover if present
        if version_info:
            pdf.set_y(10)
            pdf.set_fill_color(255, 245, 230)
            pdf.set_draw_color(255, 120, 0)
            pdf.set_line_width(0.4)
            pdf.set_x(10)
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(200, 80, 0)
            
            v_no = version_info.get("version_number", "N/A")
            pdf.cell(190, 8, f" [!] HISTORICAL ARCHIVAL RECORD - VERSION {v_no}", border='LTR', ln=True, fill=True, align='C')
            
            pdf.set_font("helvetica", "", 8)
            pdf.set_text_color(60, 60, 60)
            valid_from = ClientPDFGenerator._fmt_dt(version_info.get("valid_from"))
            valid_to = ClientPDFGenerator._fmt_dt(version_info.get("valid_to")) if version_info.get("valid_to") else "Active (Present)"
            pdf.cell(190, 6, f" Timeline: {valid_from}  TO  {valid_to}", border='LBR', ln=True, fill=True, align='C')
            
            pdf.set_line_width(0.2)
            pdf.set_y(30)
        else:
            pdf.set_y(40)

        # IA Logo
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, 85, pdf.get_y(), 40)
            pdf.set_y(pdf.get_y() + 50)
        else:
            pdf.set_y(pdf.get_y() + 20)
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(*text_black)
        ia_name = ia_data.get('name_of_entity') or ia_data.get('name_of_ia', 'Significia Investor Services')
        pdf.cell(0, 10, ia_name.upper(), ln=True, align="C")
        
        # Report Title
        pdf.ln(30)
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(*primary_blue)
        pdf.cell(0, 15, "INVESTOR REGISTRATION RECORD", ln=True, align="C")
        
        # Decorative line
        pdf.set_fill_color(*primary_blue)
        pdf.set_xy(75, pdf.get_y() + 2)
        pdf.cell(60, 1.5, "", ln=True, fill=True)
        
        # Client Main Info
        pdf.ln(40)
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*text_black)
        pdf.cell(0, 10, client_data.get('client_name', 'Unnamed Client').upper(), ln=True, align="C")
        
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, f"REFERENCE CODE: {client_data.get('client_code', 'N/A')}", ln=True, align="C")
        
        # Footer of cover page
        pdf.set_y(250)
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(150, 150, 150)
        current_date = datetime.now().strftime('%d %B %Y')
        pdf.cell(0, 6, f"Record Generated on: {current_date}", ln=True, align="C")
        
        pdf.set_font("helvetica", "", 9)
        reg_no = ia_data.get('ia_registration_number', 'N/A')
        pdf.cell(0, 6, f"Investment Advisor Reg No: {reg_no}", ln=True, align="C")
        
        # Internal Disclaimer on Cover Page
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(200, 80, 0) # Use the accent orange color for visibility
        pdf.cell(0, 8, "Internal system report - not for client communication", ln=True, align="C")

    @staticmethod
    def generate_client_report(client_data: dict, ia_data: Optional[dict] = None, version_info: Optional[dict] = None, logo_path: Optional[str] = None) -> bytes:
        pdf = BaseReportPDF(
            advisor_name=ia_data.get('name_of_ia') if ia_data else client_data.get('advisor_name'),
            entity_name=ia_data.get('name_of_entity') if ia_data else None,
            ia_reg_no=ia_data.get('ia_registration_number') if ia_data else client_data.get('advisor_registration_number')
        )
        
        # 1. Render Cover Page if IA Data is available
        if ia_data:
            ClientPDFGenerator.render_client_cover_page(pdf, client_data, ia_data, logo_path, version_info)
        
        pdf.add_page()
        margin = 10
        accent_grey = (248, 249, 250)
        border_grey = (210, 215, 220)
        text_black = (10, 10, 10)
        text_muted = (80, 80, 80)
        primary_blue = (0, 70, 160)

        # Shift Y to start sections directly
        pdf.set_draw_color(*border_grey)
        pdf.set_y(20)

        def render_compact_section(title, fields, row_h=7.5, is_last=False):
            temp_fields = [f for f in fields if f[1] is not None]
            if not temp_fields: return

            pdf.set_x(margin)
            pdf.set_font("helvetica", "B", 10.5)
            pdf.set_text_color(*primary_blue)
            pdf.set_fill_color(*accent_grey)
            pdf.cell(0, 9, f" {title.upper()}", ln=True, fill=True, border='LTBR')
            
            i = 0
            while i < len(temp_fields):
                pdf.set_x(margin)
                field1 = temp_fields[i]
                is_full1 = field1[2] if len(field1) > 2 else False
                
                field2 = None
                if not is_full1 and (i + 1) < len(temp_fields):
                    if not (len(temp_fields[i+1]) > 2 and temp_fields[i+1][2]):
                        field2 = temp_fields[i+1]

                pdf.set_fill_color(255, 255, 255) if (i // 2) % 2 == 0 else pdf.set_fill_color(254, 254, 254)

                start_y = pdf.get_y()
                val1 = str(field1[1]) if str(field1[1]).strip() != "" else "N/A"

                if is_full1:
                    if field1[0]:
                        # Render label as a bold blue header for formal sections
                        pdf.set_font("helvetica", "B", 9)
                        pdf.set_text_color(*primary_blue)
                        pdf.cell(0, 8, f" {field1[0].upper()}:", border='LTR', fill=True, ln=True)
                        
                        pdf.set_font("helvetica", "", 9)
                        pdf.set_text_color(*text_black)
                        # Slightly closer spacing for multi-line blocks
                        pdf.multi_cell(0, 5, f" {val1}", border='LBR', fill=True)
                    else:
                        pdf.set_font("helvetica", "I", 9)
                        pdf.set_text_color(*text_black)
                        pdf.multi_cell(0, 5, f" {val1}", border=1, fill=True)
                    
                    i += 1
                elif field2:
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.set_draw_color(*border_grey)
                    pdf.cell(40, row_h, f" {field1[0]}", border='LBR', fill=True)
                    
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    pdf.cell(55, row_h, f" {val1}", border='BR', fill=True)
                    
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.cell(40, row_h, f" {field2[0]}", border='BR', fill=True)
                    
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    val2 = str(field2[1]) if str(field2[1]).strip() != "" else "N/A"
                    pdf.cell(55, row_h, f" {val2}", border='RBR', fill=True, ln=True)
                    i += 2
                else:
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.cell(40, row_h, f" {field1[0]}", border='LBR', fill=True)
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    pdf.cell(0, row_h, f" {val1}", border='RBR', fill=True, ln=True)
                    i += 1
            if not is_last:
                pdf.ln(3)

        sections = [
            ("Identity Details", [
                ("Full Name", client_data.get("client_name")),
                ("DOB", client_data.get("date_of_birth")),
                ("Gender", client_data.get("gender")),
                ("Marital", client_data.get("marital_status")),
                ("PAN No.", client_data.get("pan_number", "").upper()),
                ("Nationality", client_data.get("nationality")),
                ("Identity", f"{'Aadhar' if client_data.get('residential_status') == 'Resident Individual' else 'Passport'}: {client_data.get('aadhar_number') or client_data.get('passport_number')}"),
                ("Employment", client_data.get("occupation")),
            ]),
            ("Family & Contact", [
                ("Father's Name", client_data.get("father_name")),
                ("Mother's Name", client_data.get("mother_name")),
                ("Phone No.", client_data.get("phone_number")),
                ("Email ID", client_data.get("email")),
                ("Home Address", client_data.get("address"), True),
            ]),
            ("KYC & IPV Compliance", [
                ("Assigned To", client_data.get("assigned_person_info") or "N/A"),
                ("CKYC Verified", "Yes" if client_data.get("kyc_verified") else "No"),
                ("CKYC Number", client_data.get("ckyc_number") or "N/A"),
                ("IPV Performer", client_data.get("ipv_done_by_name") or "N/A"),
                ("IPV Date", ClientPDFGenerator._fmt_dt(client_data.get("ipv_date")) if client_data.get("ipv_date") else "N/A"),
            ]),
            ("Financial Profile", [
                ("Annual Income", f"INR {float(client_data.get('annual_income', 0)):,.0f}"),
                ("Net Worth", f"INR {float(client_data.get('net_worth', 0)):,.0f}"),
                ("Income Source", client_data.get("income_source")),
                ("Risk Profile (Client Provided)", client_data.get("risk_profile")),
                ("Current Portfolio", f"INR {float(client_data.get('existing_portfolio_value', 0)):,.0f}"),
                ("Portfolio Detail", client_data.get("existing_portfolio_composition"), True),
            ]),
            ("Banking & Demat", [
                ("Bank Name", client_data.get("bank_name")),
                ("Branch", client_data.get("bank_branch")),
                ("A/C Number", client_data.get("bank_account_number")),
                ("IFSC Code", client_data.get("ifsc_code")),
                ("Demat A/C", client_data.get("demat_account_number")),
                ("Trading A/C", client_data.get("trading_account_number")),
            ]),
            ("Strategy & Compliance", [
                ("Horizon", client_data.get("investment_horizon")),
                ("Experience", client_data.get("investment_experience")),
                ("Tax Residency", client_data.get("tax_residency")),
                ("Nominee Name", client_data.get("nominee_name")),
                ("Objectives", client_data.get("investment_objectives"), True),
            ]),
            ("Document Checklist", [
                (doc, " [ Yes ]" if doc in (client_data.get("uploaded_documents") or []) else " [ No ]")
                for doc in REQUIRED_DOCUMENTS
            ]),
            ("Regulatory Declaration & IA Consent", [
                ("Agreement Date", client_data.get("agreement_date")),
                ("Investment Advisor", client_data.get("advisor_name")),
                ("Compliance Declaration Statement", "I hereby confirm that all details provided are accurate to the best of my knowledge. This report is generated based on client provided data and recorded information. This report is for data recording and financial analysis purpose only and does not constitute investment advice or recommendation. The client's identity has been verified via KYC documents. The report is generated for internal use and analytical purposes only. All information has been provided by the client and recorded by the Investment Advisor. The system does not independently verify such information. Client consents to use of data for financial analysis and regulatory compliance purposes.", True),
            ])
        ]

        for i, (title, fields) in enumerate(sections):
            is_last = (i == len(sections) - 1)
            
            # Prevent awkward page breaks for the bottom legal sections
            if i >= len(sections) - 2 and pdf.get_y() > 180:
                pdf.add_page()
            elif pdf.get_y() > 230:
                pdf.add_page()
                
            render_compact_section(title, fields, is_last=is_last)

        return bytes(pdf.output())

    @staticmethod
    def generate_client_master_report(clients: List[dict], ia_data: Optional[dict] = None) -> bytes:
        pdf = BaseReportPDF(
            orientation="L",
            advisor_name=ia_data.get('name_of_ia') if ia_data else None,
            entity_name=ia_data.get('name_of_entity') if ia_data else None,
            ia_reg_no=ia_data.get('ia_registration_number') if ia_data else None
        )
        pdf.add_page()
        
        accent_grey = (248, 249, 250)
        border_grey = (210, 215, 220)
        text_black = (10, 10, 10)
        text_muted = (80, 80, 80)
        primary_blue = (0, 70, 160)
        
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*text_black)
        current_date_str = datetime.now().strftime('%d-%m-%Y')
        pdf.cell(0, 10, f"ACTIVE CLIENT CODE MASTER UPDATE STATUS AS ON {current_date_str}", ln=True, align="C")
        
        if ia_data:
            entity_name = ia_data.get('name_of_entity') or ia_data.get('name_of_ia', 'N/A')
            ia_reg = ia_data.get('ia_registration_number', 'N/A')
            pdf.set_font("helvetica", "B", 11)
            pdf.set_text_color(*text_muted)
            pdf.cell(0, 6, f"ENTITY: {entity_name.upper()}", ln=True, align="C")
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, f"IA REGISTRATION NO: {ia_reg}", ln=True, align="C")
            pdf.ln(2)

        pdf.ln(5)
        
        headers = [
            ("SL No", 10),
            ("Client Code", 20),
            ("Client Name", 32),
            ("PAN Number", 22),
            ("CKYC No", 25),
            ("DOB", 18),
            ("Reg No", 24),
            ("Advisor Name", 28),
            ("IPV", 12),
            ("Assigned Professional", 32),
            ("Created At", 25)
        ]
        
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(*primary_blue)
        pdf.set_text_color(255, 255, 255)
        pdf.set_draw_color(*border_grey)
        
        for header, width in headers:
            pdf.cell(width, 10, header, border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(*text_black)
        
        alternate = False
        for idx, client in enumerate(clients, 1):
            if alternate:
                pdf.set_fill_color(*accent_grey)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            def fmt_date(d):
                if isinstance(d, (datetime, date)):
                    return d.strftime('%d-%m-%Y')
                if isinstance(d, str) and 'T' in d:
                    try:
                        dt_obj = datetime.fromisoformat(d.replace('Z', '+00:00'))
                        return dt_obj.strftime('%d-%m-%Y')
                    except:
                        return d[:10]
                return str(d) if d else ""

            row_data = [
                (idx, 10),
                (client.get("client_code", ""), 20),
                (client.get("client_name", "")[:20], 32),
                (client.get("pan_number", "").upper(), 22),
                (client.get("ckyc_number") or "N/A", 25),
                (fmt_date(client.get("date_of_birth")), 18),
                (client.get("advisor_registration_number", ""), 24),
                (client.get("advisor_name", "")[:15], 28),
                ("DONE" if client.get("ipv_date") else "PENDING", 12),
                (client.get("employee_name", "Unassigned")[:20], 32),
                (fmt_date(client.get("created_at")), 25)
            ]
            
            for val, width in row_data:
                pdf.cell(width, 8, str(val), border=1, align="C", fill=True)
            pdf.ln()
            alternate = not alternate
            
        return bytes(pdf.output())
        