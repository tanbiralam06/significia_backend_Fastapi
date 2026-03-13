import io
from datetime import datetime
from fpdf import FPDF
from typing import List

class IAPDFGenerator:
    @staticmethod
    def generate_ia_report(ia_data: dict, employees: List[dict]) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        
        # Add Logo if exists (simulated for now with text box if path exists)
        # In a real scenario, we'd use pdf.image(ia_data['ia_logo_path'], ...)
        
        # Set font
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(33, 37, 41) # Dark grey
        pdf.cell(0, 15, "INVESTMENT ADVISOR MASTER REPORT", ln=True, align="C")
        
        pdf.set_font("helvetica", "I", 10)
        pdf.set_text_color(108, 117, 125) # Muted grey
        current_date = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        pdf.cell(0, 10, f"Generated on: {current_date}", ln=True, align="R")
        pdf.ln(5)

        # Draw a horizontal line using a thin cell
        pdf.set_fill_color(0, 123, 255) # Primary blue
        pdf.cell(0, 1, "", ln=True, fill=True)
        pdf.ln(10)
        
        # Section Header helper
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
        
        # Employee Details Section
        if employees:
            pdf.ln(10)
            section_header("Registered Professionals (Employees)")
            
            # Table Header
            pdf.set_fill_color(248, 249, 250)
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(50, 10, "Name", 1, 0, 'C', fill=True)
            pdf.cell(50, 10, "Designation", 1, 0, 'C', fill=True)
            pdf.cell(40, 10, "IA Reg No", 1, 0, 'C', fill=True)
            pdf.cell(50, 10, "Expiry Date", 1, 1, 'C', fill=True)
            
            pdf.set_font("helvetica", "", 9)
            for emp in employees:
                # Use multi_cell for name if it's too long, or just truncate for now to keep table clean
                name = emp.get('name_of_employee', '')[:25]
                designation = emp.get('designation', '')[:25]
                reg_no = emp.get('ia_registration_number', '')
                expiry = str(emp.get('date_of_registration_expiry', ''))
                
                pdf.cell(50, 10, name, 1, 0, 'L')
                pdf.cell(50, 10, designation, 1, 0, 'L')
                pdf.cell(40, 10, reg_no, 1, 0, 'C')
                pdf.cell(50, 10, expiry, 1, 1, 'C')

        # Return the PDF bytes
        return bytes(pdf.output())

class ClientPDFGenerator:
    @staticmethod
    def generate_client_report(client_data: dict) -> bytes:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=5) # Reduced margin to prevent early breakage
        pdf.add_page()
        
        # Color Palette
        accent_grey = (248, 249, 250)
        border_grey = (210, 215, 220)
        text_black = (10, 10, 10)
        text_muted = (80, 80, 80)
        primary_blue = (0, 70, 160)
        margin = 10

        # Header - Ultra compact
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(*text_black)
        pdf.cell(0, 10, "CLIENT REGISTRATION REPORT", ln=True, align="L")
        
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*primary_blue)
        pdf.cell(0, 5, f"REFERENCE: {client_data.get('client_code')}", ln=True, align="L")

        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(*text_muted)
        current_date = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        pdf.set_xy(10, 10)
        pdf.cell(0, 10, f"DATE: {current_date}", ln=True, align="R")
        pdf.set_y(25)

        def render_compact_section(title, fields, row_h=7.5, is_last=False):
            temp_fields = [f for f in fields if f[1] is not None]
            if not temp_fields: return

            # Section Title
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

                # Store starting position for full-width rows to handle label height matching
                start_y = pdf.get_y()
                val1 = str(field1[1]) if str(field1[1]).strip() != "" else "N/A"

                if is_full1:
                    # Render value first to get height, but we need to render label too.
                    # We'll calculate height of multi_cell first
                    pdf.set_font("helvetica", "", 10)
                    # We use a temp calculation or just render label and then multi_cell
                    # Labels for full width are taller
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.set_draw_color(*border_grey)
                    
                    # For full width, we render the value with multi_cell and then 
                    # go back to draw the label with the same height
                    pdf.set_x(margin + 40)
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    pdf.multi_cell(0, row_h, f" {val1}", border='RBR', fill=True)
                    end_y = pdf.get_y()
                    final_h = end_y - start_y
                    
                    # Go back and draw label
                    pdf.set_xy(margin, start_y)
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.cell(40, final_h, f" {field1[0]}", border='LBR', fill=True)
                    pdf.set_y(end_y)
                    i += 1
                elif field2:
                    # Side by Side
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.set_draw_color(*border_grey)
                    pdf.cell(40, row_h, f" {field1[0]}", border='LBR', fill=True)
                    
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    pdf.cell(55, row_h, f" {val1}", border='BR', fill=True)
                    
                    # Col 2
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*text_muted)
                    pdf.cell(40, row_h, f" {field2[0]}", border='BR', fill=True)
                    
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(*text_black)
                    val2 = str(field2[1]) if str(field2[1]).strip() != "" else "N/A"
                    pdf.cell(55, row_h, f" {val2}", border='RBR', fill=True, ln=True)
                    i += 2
                else:
                    # Single but not full width
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
                ("Risk Profile", client_data.get("risk_profile")),
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
                ("Reg. Date", client_data.get("declaration_date")),
                ("IA Master", client_data.get("advisor_name")),
                ("Statement", "I hereby confirm that all details provided are accurate to the best of my knowledge and comply with SEBI Investment Advisor guidelines. The client's identity has been verified via KYC documents.", True),
            ])
        ]

        for i, (title, fields) in enumerate(sections):
            is_last = (i == len(sections) - 1)
            render_compact_section(title, fields, is_last=is_last)

        # Footer - Positioned strictly from bottom
        pdf.set_y(-12)
        pdf.set_x(margin)
        pdf.set_draw_color(*primary_blue)
        pdf.cell(0, 0.2, "", ln=True, fill=True)
        pdf.set_font("helvetica", "B", 6)
        pdf.set_text_color(*text_muted)
        pdf.cell(0, 6, "OFFICIAL CLIENT RECORD - SIGNIFICIA SECURE PLATFORM", ln=False, align="L")
        pdf.set_font("helvetica", "I", 6)
        pdf.cell(0, 6, "Page 1 / 1", ln=False, align="R")

        return bytes(pdf.output())

