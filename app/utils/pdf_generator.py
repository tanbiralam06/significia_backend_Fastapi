import io
import os
from datetime import datetime, date
from fpdf import FPDF
from typing import List, Optional

class BaseReportPDF(FPDF):
    def __init__(self, *args, **kwargs):
        self.advisor_name = kwargs.pop('advisor_name', "")
        self.entity_name = kwargs.pop('entity_name', "")
        self.ia_reg_no = kwargs.pop('ia_reg_no', "")
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

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
    def generate_ia_report(ia_data: dict, employees: List[dict], logo_path: Optional[str] = None) -> bytes:
        pdf = BaseReportPDF(
            advisor_name=ia_data.get('name_of_ia', ''),
            entity_name=ia_data.get('name_of_entity', ''),
            ia_reg_no=ia_data.get('ia_registration_number', '')
        )
        pdf.add_page()
        
        # Set font
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(33, 37, 41) # Dark grey
        
        # Add Logo if available
        if logo_path and os.path.exists(logo_path):
            try:
                # Add logo at top left
                pdf.image(logo_path, 10, 8, 33)
                pdf.set_x(50) # Move text to the right of logo
                pdf.cell(0, 15, "INVESTMENT ADVISOR MASTER REPORT", ln=True, align="L")
            except Exception as e:
                print(f"Error rendering logo in IA Master Report: {e}")
                pdf.cell(0, 15, "INVESTMENT ADVISOR MASTER REPORT", ln=True, align="C")
        else:
            pdf.cell(0, 15, "INVESTMENT ADVISOR MASTER REPORT", ln=True, align="C")
        
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(108, 117, 125) # Muted grey
        current_date = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        pdf.cell(0, 10, f"Generated on: {current_date}", ln=True, align="R")
        pdf.ln(5)

        # Draw a horizontal line matching premium aesthetics
        pdf.set_fill_color(0, 123, 255) # Primary blue
        pdf.cell(0, 1, "", ln=True, fill=True)
        pdf.ln(10)
        
        def section_header(title):
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(0, 123, 255)
            pdf.cell(0, 10, title, ln=True)
            pdf.ln(2)

        section_header("Investment Advisor Profile")
        
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(33, 37, 41)
        
        fields = [
            ("Name of IA", ia_data.get('name_of_ia')),
            ("Nature of Entity", ia_data.get('nature_of_entity', '').capitalize()),
            ("Entity Name", ia_data.get('name_of_entity') or "N/A"),
            ("Reg Number", ia_data.get('ia_registration_number')),
            ("Reg Date", str(ia_data.get('date_of_registration'))),
            ("Expiry Date", str(ia_data.get('date_of_registration_expiry'))),
            ("Address", ia_data.get('registered_address')),
            ("Email", ia_data.get('registered_email_id')),
            ("Phone", ia_data.get('registered_contact_number'))
        ]
        
        for field, value in fields:
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(50, 8, f"{field}:", 0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 8, str(value), 0, ln=True)
        
        pdf.ln(10)
        section_header("Bank Details")
        
        bank_fields = [
            ("A/C Number", ia_data.get('bank_account_number')),
            ("Bank Name", ia_data.get('bank_name')),
            ("Branch", ia_data.get('bank_branch')),
            ("IFSC Code", ia_data.get('ifsc_code'))
        ]
        
        for field, value in bank_fields:
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(50, 8, f"{field}:", 0)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 8, str(value), 0, ln=True)
        
        if employees:
            pdf.ln(10)
            section_header("Registered Professionals (Employees)")
            
            pdf.set_fill_color(248, 249, 250)
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(50, 10, "Name", 1, 0, 'C', fill=True)
            pdf.cell(50, 10, "Designation", 1, 0, 'C', fill=True)
            pdf.cell(40, 10, "IA Reg No", 1, 0, 'C', fill=True)
            pdf.cell(50, 10, "Expiry Date", 1, 1, 'C', fill=True)
            
            pdf.set_font("helvetica", "", 9)
            for emp in employees:
                name = emp.get('name_of_employee', '')[:25]
                designation = emp.get('designation', '')[:25]
                reg_no = emp.get('ia_registration_number', '')
                expiry = str(emp.get('date_of_registration_expiry', ''))
                
                pdf.cell(50, 10, name, 1, 0, 'L')
                pdf.cell(50, 10, designation, 1, 0, 'L')
                pdf.cell(40, 10, reg_no, 1, 0, 'C')
                pdf.cell(50, 10, expiry, 1, 1, 'C')

        return bytes(pdf.output())

class ClientPDFGenerator:
    @staticmethod
    def generate_client_report(client_data: dict, ia_data: Optional[dict] = None) -> bytes:
        pdf = BaseReportPDF(
            advisor_name=ia_data.get('name_of_ia') if ia_data else client_data.get('advisor_name'),
            entity_name=ia_data.get('name_of_entity') if ia_data else None,
            ia_reg_no=ia_data.get('ia_registration_number') if ia_data else client_data.get('advisor_registration_number')
        )
        pdf.add_page()
        
        accent_grey = (248, 249, 250)
        border_grey = (210, 215, 220)
        text_black = (10, 10, 10)
        text_muted = (80, 80, 80)
        primary_blue = (0, 70, 160)
        margin = 10

        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(*text_black)
        pdf.cell(0, 10, "CLIENT REGISTRATION REPORT", ln=True, align="L")
        
        if ia_data:
            entity_name = ia_data.get('name_of_entity') or ia_data.get('name_of_ia', 'N/A')
            ia_reg = ia_data.get('ia_registration_number', 'N/A')
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(*text_muted)
            pdf.cell(0, 5, f"ENTITY: {entity_name.upper()}", ln=True, align="L")
            pdf.cell(0, 5, f"REGISTRATION NO: {ia_reg}", ln=True, align="L")

        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*primary_blue)
        pdf.cell(0, 5, f"REFERENCE: {client_data.get('client_code')}", ln=True, align="L")

        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(*text_muted)
        current_date = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        pdf.set_xy(10, 10)
        pdf.cell(0, 10, f"DATE: {current_date}", ln=True, align="R")
        # Shift Y down if header is present
        pdf.set_y(40 if ia_data else 25)

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
                    pdf.set_x(margin + 40)
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    pdf.multi_cell(0, row_h, f" {val1}", border='RBR', fill=True)
                    end_y = pdf.get_y()
                    final_h = end_y - start_y
                    
                    pdf.set_xy(margin, start_y)
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.cell(40, final_h, f" {field1[0]}", border='LBR', fill=True)
                    pdf.set_y(end_y)
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
            ("Declaration", [
                ("Agreement Date", client_data.get("agreement_date")),
                ("IA Master", client_data.get("advisor_name")),
                ("Statement", "I hereby confirm that all details provided are accurate to the best of my knowledge. This report is generated based on client provided data and recorded information. This report is for data recording and financia analysis purpose only and does not constitute investment advice or recommendation. The client's identity has been verified via KYC documents. The report is generated for internal use and analytical purposes only. All information has been provided by the client and recorded by the Investment Advisor. The system does not independently verify such information. Client consents to use of data for financial analysis and regulatory compliance purposes.", True),
            ])
        ]

        for i, (title, fields) in enumerate(sections):
            is_last = (i == len(sections) - 1)
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
            ("SL No", 12),
            ("Client Code", 22),
            ("Client Name", 38),
            ("PAN Number", 25),
            ("DOB", 20),
            ("Reg No", 30),
            ("Advisor Name", 33),
            ("Relation", 15),
            ("Assigned Employee", 35),
            ("Created At", 30)
        ]
        
        pdf.set_font("helvetica", "B", 9)
        pdf.set_fill_color(*primary_blue)
        pdf.set_text_color(255, 255, 255)
        pdf.set_draw_color(*border_grey)
        
        for header, width in headers:
            pdf.cell(width, 10, header, border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*text_black)
        
        alternate = False
        for idx, client in enumerate(clients, 1):
            if alternate:
                pdf.set_fill_color(*accent_grey)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            def fmt_date(d):
                if isinstance(d, (datetime, date)):
                    return d.strftime('%d-%m-%Y %H:%M')
                if isinstance(d, str) and 'T' in d:
                    try:
                        # Attempt to parse ISO format and extracted date + HH:MM
                        dt_obj = datetime.fromisoformat(d.replace('Z', '+00:00'))
                        return dt_obj.strftime('%d-%m-%Y %H:%M')
                    except:
                        # Fallback parsing YYYY-MM-DD
                        return d[:16].replace('T', ' ') # Simple fallback: YYYY-MM-DD HH:MM
                return str(d) if d else ""

            row_data = [
                (idx, 12),
                (client.get("client_code", ""), 22),
                (client.get("client_name", "")[:20], 38),
                (client.get("pan_number", "").upper(), 25),
                (fmt_date(client.get("date_of_birth")), 20),
                (client.get("advisor_registration_number", ""), 30),
                (client.get("advisor_name", "")[:20], 33),
                (client.get("relation", "self"), 15),
                (client.get("employee_name", "Unassigned")[:20], 35),
                (fmt_date(client.get("created_at")), 30)
            ]
            
            for val, width in row_data:
                pdf.cell(width, 8, str(val), border=1, align="C", fill=True)
            pdf.ln()
            alternate = not alternate
            
        return bytes(pdf.output())
        