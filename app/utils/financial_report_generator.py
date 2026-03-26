"""
Financial Report Generator — PDF and Word Document Generation.
Adapted from finplan.py with SQLAlchemy support and modern styling.
"""
import os
import io
import re
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# PDF generation imports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    PDF_AVAILABLE = True
    
    class NumberedCanvas(canvas.Canvas):
        """Custom PDF Canvas class with 'Page x of y' in footer."""
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_number(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_number(self, page_count):
            self.setFont("Helvetica", 9)
            current_page = self._pageNumber
            text = f"Page {current_page} of {page_count}"
            self.drawCentredString(300, 20, text)

except ImportError:
    PDF_AVAILABLE = False
    
    class NumberedCanvas:
        """Dummy class when reportlab is missing."""
        def __init__(self, *args, **kwargs):
            pass

# Word document generation imports
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False


def format_currency(value) -> str:
    """Format currency value without decimal places (Rs 1,00,000)."""
    try:
        if value is None:
            return "Rs 0"
        return f"Rs {int(float(value)):,}"
    except (ValueError, TypeError):
        return "Rs 0"


class FinancialReportGenerator:
    """
    Generate PDF and Word reports with full parity to legacy finplan.py.
    """

    @staticmethod
    def generate_pdf(result: Any, profile: Any, client_name: str, ia_logo_path: Optional[str] = None) -> io.BytesIO:
        """Generate PDF report as a byte stream with 15 sections."""
        if not PDF_AVAILABLE:
            raise ImportError("reportlab is not installed.")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Styles matching legacy
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, alignment=1, spaceAfter=30)
        subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=18, alignment=1, spaceAfter=20)
        section_style = ParagraphStyle('CustomSection', parent=styles['Heading2'], fontSize=16, spaceBefore=20, spaceAfter=10)
        subsection_style = ParagraphStyle('CustomSubsection', parent=styles['Heading3'], fontSize=14, spaceBefore=15, spaceAfter=8)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)
        bold_style = ParagraphStyle('CustomBold', parent=styles['Normal'], fontSize=10, spaceAfter=6, fontName='Helvetica-Bold')

        # Header with Logo
        if ia_logo_path and os.path.exists(ia_logo_path):
            try:
                header_data = [[
                    Image(ia_logo_path, width=1.2*inch, height=1.2*inch, hAlign='LEFT'),
                    Paragraph('COMPREHENSIVE FINANCIAL ANALYSIS REPORT', title_style)
                ]]
                header_table = Table(header_data, colWidths=[1.5*inch, 5*inch])
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (0, 0), 0),
                    ('RIGHTPADDING', (0, 0), (0, 0), 10),
                ]))
                elements.append(header_table)
            except:
                elements.append(Paragraph("COMPREHENSIVE FINANCIAL ANALYSIS REPORT", title_style))
        else:
            elements.append(Paragraph("COMPREHENSIVE FINANCIAL ANALYSIS REPORT", title_style))

        elements.append(Paragraph(f"Client: {client_name}", subtitle_style))

        # IA Info
        if profile.client.client_code:
            elements.append(Paragraph(f"Client Code: {profile.client.client_code}", normal_style))
        if profile.client.advisor_name:
            elements.append(Paragraph(f"Investment Advisor: {profile.client.advisor_name}", normal_style))
            if profile.client.advisor_registration_number:
                elements.append(Paragraph(f"IA Registration Number: {profile.client.advisor_registration_number}", normal_style))

        elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%d %B, %Y')}", normal_style))
        elements.append(Spacer(1, 20))

        # 1. CLIENT INFORMATION
        elements.append(Paragraph('1. Client Information', section_style))

        # 1.1 Basic Info
        elements.append(Paragraph('1.1 Client Basic Information', subsection_style))
        basic_data = [
            ['Particulars', 'Details'],
            ['Occupation', profile.occupation],
            ['Date of Birth', str(profile.dob)],
            ['Annual Income', format_currency(profile.annual_income)],
            ['Email ID', profile.email or 'Not provided'],
            ['PAN Number', profile.pan or 'Not provided']
        ]
        t = Table(basic_data, colWidths=[200, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.white)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.2 Spouse Info
        elements.append(Paragraph('1.2 Spouse Information', subsection_style))
        spouse_data = [
            ['Particulars', 'Details'],
            ['Spouse Name', profile.spouse_name or 'Not provided'],
            ['Date of Birth', str(profile.spouse_dob) if profile.spouse_dob else 'Not provided'],
            ['Occupation', profile.spouse_occupation or 'Not provided']
        ]
        t = Table(spouse_data, colWidths=[200, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.white)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.3 Children Info
        if profile.children:
            elements.append(Paragraph('1.3 Children Information', subsection_style))
            child_data = [['Child Name', 'Date of Birth', 'Occupation/Status']]
            for child in profile.children:
                child_data.append([child.get('name', 'N/A'), child.get('dob', 'N/A'), child.get('occupation', 'N/A')])
            t = Table(child_data, colWidths=[150, 150, 200])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))

        # 1.4 Contact & Identification
        elements.append(Paragraph('1.4 Contact & Identification', subsection_style))
        contact_data = [
            ['Particulars', 'Details'],
            ['Address', profile.client.address or 'Not provided'],
            ['Contact Number', profile.contact]
        ]
        t = Table(contact_data, colWidths=[200, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,1), (-1,-1), colors.white)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.5 Expenses Breakdown
        elements.append(Paragraph('1.5 Annual Expenses', subsection_style))
        exp_cats = {
            'hh': 'Household & Groceries', 'med': 'Medical & Healthcare', 'travel': 'Travel & Transportation',
            'elec': 'Electricity & Utilities', 'tele': 'Telephone & Internet', 'maid': 'Maid & Domestic Help',
            'edu': 'Education & Children', 'ent': 'Entertainment & Leisure', 'emi': 'EMI Paid',
            'savings': 'Savings/Investment CONTRIBUTION', 'misc': 'Miscellaneous Expenses'
        }
        exp_data = [['Expense Category', 'Amount']]
        total_exp = 0
        for k, v in exp_cats.items():
            amt = profile.expenses.get(k, 0)
            if amt > 0:
                exp_data.append([v, format_currency(amt)])
                total_exp += amt
        exp_data.append(['TOTAL ANNUAL EXPENSES', format_currency(total_exp)])
        t = Table(exp_data, colWidths=[300, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.6 & 1.7 Assets and Liabilities
        elements.append(Paragraph('1.6 Assets & 1.7 Liabilities', subsection_style))
        ast_data = [['Asset Category', 'Amount']]
        ast_map = {'land': 'Land & Building', 'inv': 'Investments', 'cash': 'Cash at Bank', 'retirement': 'Retirement Savings'}
        total_ast = 0
        for k, label in ast_map.items():
            v = profile.assets.get(k, 0)
            if v > 0:
                ast_data.append([label, format_currency(v)])
                total_ast += v
        ast_data.append(['TOTAL ASSETS', format_currency(total_ast)])
        t = Table(ast_data, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 6))

        lib_data = [['Liability Category', 'Amount']]
        lib_map = {'personal': 'Personal Loan', 'cc': 'Credit Card', 'hb': 'Home/Building Loan'}
        total_lib = 0
        # Standard liabilities
        for k, label in lib_map.items():
            v = profile.liabilities.get(k, 0)
            if v > 0:
                lib_data.append([label, format_currency(v)])
                total_lib += v
                
        # Custom "Other" liabilities
        others = profile.liabilities.get('others', [])
        if isinstance(others, list):
            for other in others:
                amt = other.get('amount', 0) if isinstance(other, dict) else getattr(other, 'amount', 0)
                if amt > 0:
                    label = other.get('label', 'Other') if isinstance(other, dict) else getattr(other, 'label', 'Other')
                    lib_data.append([label, format_currency(amt)])
                    total_lib += amt

        lib_data.append(['TOTAL LIABILITIES', format_currency(total_lib)])
        t = Table(lib_data, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.8 Net Worth Calculation
        elements.append(Paragraph('1.8 Net Worth Calculation', subsection_style))
        net_worth = total_ast - total_lib
        net_worth_data = [
            ['Total Assets', format_currency(total_ast)],
            ['Total Liabilities', format_currency(total_lib)],
            ['NET WORTH (Assets - Liabilities)', format_currency(net_worth)]
        ]
        t = Table(net_worth_data, colWidths=[300, 200])
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 1.9 Current Insurance Cover
        elements.append(Paragraph('1.9 Current Insurance Cover', subsection_style))
        ins_data = [
            ['Insurance Type', 'Cover Amount', 'Premium'],
            ['Life Insurance', format_currency(profile.insurance.get('life_cover', 0)), format_currency(profile.insurance.get('life_premium', 0))],
            ['Medical Cover', format_currency(profile.insurance.get('medical_cover', 0)), format_currency(profile.insurance.get('medical_premium', 0))],
            ['Vehicle insurance', format_currency(profile.insurance.get('vehicle_cover', 0)), format_currency(profile.insurance.get('vehicle_premium', 0))],
        ]
        t = Table(ins_data, colWidths=[200, 150, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # 2. Financial Assumptions
        elements.append(Paragraph('2. Financial Assumptions', section_style))
        ass_data = [['Parameter', 'Value']]
        for k, v in profile.assumptions.items():
            ass_data.append([k.replace('_', ' ').title(), f"{v}%" if 'rate' in k or 'inflation' in k or 'sol' in k else str(v)])
        t = Table(ass_data, colWidths=[250, 250])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(PageBreak())

        # 3. AI Executive Brief
        if not profile.exclude_ai and result.ai_analysis and 'executive_brief' in result.ai_analysis:
            elements.append(Paragraph('Executive Summary & Insights', section_style))
            brief = result.ai_analysis['executive_brief']
            # Remove any HTML tags if they exist (though usually they don't in PDF generator)
            brief = re.sub(r'<[^>]*>', '', brief)
            elements.append(Paragraph(brief, normal_style))
            elements.append(Spacer(1, 12))

        # 4. HLV
        elements.append(Paragraph('4. Human Life Value Analysis', section_style))
        hlv = result.hlv_data
        hlv_info = [
            ['Description', 'Value'],
            ['HLV (Income Replacement Method)', format_currency(hlv.get('hlv_income_method'))],
            ['HLV (Need Based Method)', format_currency(hlv.get('hlv_expense_method'))],
            ['Net HLV (Income)', format_currency(hlv.get('net_hlv_income'))],
            ['Additional Life Cover Needed (Income)', format_currency(hlv.get('additional_life_cover_needed_income'))],
            ['Current Life Cover', format_currency(profile.insurance.get('life_cover', 0))],
        ]
        t = Table(hlv_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # AI HLV Comments
        if not profile.exclude_ai and result.ai_analysis and 'hlv_comments' in result.ai_analysis:
            elements.append(Paragraph('System Insights (HLV):', subsection_style))
            for comment in result.ai_analysis['hlv_comments']:
                elements.append(Paragraph(f"• {comment}", normal_style))
            elements.append(Spacer(1, 6))

        # 5. Medical
        elements.append(Paragraph('5. Medical Coverage Analysis', section_style))
        med = result.medical_data
        med_info = [
            ['Description', 'Value'],
            ['Medical Corpus at Retirement', format_currency(med.get('medical_corpus_at_retirement'))],
            ['Medical Corpus at Life Expectancy', format_currency(med.get('medical_corpus_at_life_expectancy'))],
            ['Balance Needed at Retirement', format_currency(med.get('balance_needed_at_retirement'))],
        ]
        t = Table(med_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # AI Medical Comments
        if not profile.exclude_ai and result.ai_analysis and 'medical_comments' in result.ai_analysis:
            elements.append(Paragraph('System Insights (Medical):', subsection_style))
            for comment in result.ai_analysis['medical_comments']:
                elements.append(Paragraph(f"• {comment}", normal_style))
            elements.append(Spacer(1, 6))

        # 6. Retirement
        elements.append(Paragraph('6. Retirement Corpus Analysis', section_style))
        ret = result.calculations
        ret_info = [
            ['Description', 'Value'],
            ['Retirement Corpus Needed', format_currency(ret.get('retirement_corpus_at_retirement'))],
            ['Net Corpus Needed', format_currency(ret.get('net_retirement_corpus_needed'))],
            ['Retirement Readiness', f"{ret.get('retirement_readiness', 0)}%"],
        ]
        t = Table(ret_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # AI Retirement Comments
        if not profile.exclude_ai and result.ai_analysis and 'retirement_comments' in result.ai_analysis:
            elements.append(Paragraph('System Insights (Retirement):', subsection_style))
            for comment in result.ai_analysis['retirement_comments']:
                elements.append(Paragraph(f"• {comment}", normal_style))
            elements.append(Spacer(1, 6))

        # 7. Cash Flow Table
        if result.cash_flow_analysis:
            elements.append(PageBreak())
            elements.append(Paragraph('7. Retirement Cash Flow Analysis', section_style))
            cf = result.cash_flow_analysis
            cf_data = [['Year', 'Age', 'Opening Bal', 'Growth', 'Withdrawal', 'Closing Bal']]
            for row in cf:
                cf_data.append([str(row['year']), str(row['retirement_age_year']), format_currency(row['opening_balance']), 
                                format_currency(row['investment_growth']), format_currency(row['annual_withdrawal']), format_currency(row['closing_balance'])])
            
            t = Table(cf_data, colWidths=[40, 40, 100, 100, 100, 100])
            t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
            elements.append(t)

        # 8. Child Goals
        elements.append(Paragraph('8. Child Goals Analysis', section_style))
        edu_info = [
            ['Education Today Value', format_currency(result.calculations.get('education_corpus_today', 0))],
            ['Education Future Needed', format_currency(result.calculations.get('education_future_needed', 0))],
            ['Education Net Corpus', format_currency(result.calculations.get('education_net_corpus', 0))],
            ['Education Monthly Investment', format_currency(result.calculations.get('monthly_investment_education', 0))],
        ]
        t = Table(edu_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 6))

        marr_info = [
            ['Marriage Today Value', format_currency(result.calculations.get('marriage_corpus_today', 0))],
            ['Marriage Future Needed', format_currency(result.calculations.get('marriage_future_needed', 0))],
            ['Marriage Net Corpus', format_currency(result.calculations.get('marriage_net_corpus', 0))],
            ['Marriage Monthly Investment', format_currency(result.calculations.get('monthly_investment_marriage', 0))],
        ]
        t = Table(marr_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 9. Emergency Fund Analysis
        elements.append(Paragraph('9. Emergency Fund Analysis', section_style))
        em_info = [
            ['Emergency Fund Needed (6 months)', format_currency(result.calculations.get('emergency_fund_needed', 0))],
            ['Shortfall', format_currency(result.calculations.get('emergency_fund_shortfall', 0))],
            ['Monthly Investment Required', format_currency(result.calculations.get('monthly_investment_emergency', 0))],
        ]
        t = Table(em_info, colWidths=[300, 200])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 10. Summary Table
        elements.append(Paragraph('10. Monthly Investment Summary', section_style))
        inv_data = [
            ['Investment Goal', 'Monthly Investment', 'Months'],
            ['Retirement', format_currency(ret.get('monthly_investment_retirement')), str(int(ret.get('years_to_retirement', 0)*12))],
            ['Education', format_currency(ret.get('monthly_investment_education')), str(int(profile.assumptions.get('education_years', 0)*12))],
            ['Marriage', format_currency(ret.get('monthly_investment_marriage')), str(int(profile.assumptions.get('marriage_years', 0)*12))],
            ['TOTAL (Income Method)', format_currency(ret.get('total_monthly_investment_income')), ''],
            ['TOTAL (Expense Method)', format_currency(ret.get('total_monthly_investment_expense')), '']
        ]
        t = Table(inv_data, colWidths=[200, 150, 100])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)

        # 11. Investment Allocation
        elements.append(Paragraph('11. Existing Investment Allocation(%)', section_style))
        all_data = [
            ['Goal', 'Allocation Percentage'],
            ['Education Goal', f"{profile.education_investment_pct}%"],
            ['Marriage Goal', f"{profile.marriage_investment_pct}%"],
        ]
        t = Table(all_data, colWidths=[250, 250])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 12. Financial Health Score
        elements.append(Paragraph('12. Financial Health Score', section_style))
        score_data = [['Component', 'Status/Value', 'Points Awarded']]
        for component, status, points in result.calculations.get('financial_health_score_details', []):
            score_data.append([component, str(status), str(points)])
        score_data.append(['TOTAL SCORE', '', f"{result.financial_health_score}/100"])
        t = Table(score_data, colWidths=[200, 200, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # 13. System Conclusion
        if not profile.exclude_ai and result.ai_analysis and 'overall_conclusion' in result.ai_analysis:
            elements.append(Paragraph('13. OVERALL CONCLUSION', section_style))
            conc = result.ai_analysis['overall_conclusion']
            conc = re.sub(r'<[^>]*>', '', conc)
            elements.append(Paragraph(conc, normal_style))
            elements.append(Spacer(1, 20))

        # 14. Disclaimer
        elements.append(PageBreak())
        elements.append(Paragraph('14. DISCLAIMER', section_style))
        disc = profile.disclaimer_text or "This report is generated based on data provided by the client..."
        elements.append(Paragraph(disc, normal_style))

        # 15. Discussion Notes
        if profile.discussion_notes:
            elements.append(Paragraph('15. DISCUSSION NOTES', section_style))
            elements.append(Paragraph(profile.discussion_notes, normal_style))

        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_docx(result: Any, profile: Any, client_name: str, ia_logo_path: Optional[str] = None) -> io.BytesIO:
        """Generate Word report as a byte stream with 15 sections."""
        if not WORD_AVAILABLE:
            raise ImportError("python-docx is not installed.")

        doc = Document()
        doc.add_heading("COMPREHENSIVE FINANCIAL ANALYSIS REPORT", 0)
        doc.add_paragraph(f"Client: {client_name}")
        doc.add_paragraph(f"Date: {datetime.now().strftime('%d %B, %Y')}")

        def add_table(title, data):
            doc.add_heading(title, level=1)
            table = doc.add_table(rows=len(data), cols=len(data[0]))
            table.style = 'Table Grid'
            for i, row in enumerate(data):
                for j, val in enumerate(row):
                    table.cell(i, j).text = str(val)

        # 1. Client Profile
        add_table("1.1 Basic Information", [
            ["Particulars", "Details"],
            ["Name", client_name],
            ["Date of Birth", str(profile.dob)],
            ["Occupation", profile.occupation],
            ["Annual Income", format_currency(profile.annual_income)]
        ])

        if profile.spouse_name:
            add_table("1.2 Spouse Information", [
                ["Particulars", "Details"],
                ["Name", profile.spouse_name],
                ["Occupation", profile.spouse_occupation or "N/A"]
            ])

        # 1.5 Expenses
        exp_cats = {
            'hh': 'Household & Groceries', 'med': 'Medical & Healthcare', 'travel': 'Travel & Transportation',
            'elec': 'Electricity & Utilities', 'tele': 'Telephone & Internet', 'maid': 'Maid & Domestic Help',
            'edu': 'Education & Children', 'ent': 'Entertainment & Leisure', 'emi': 'EMI Paid',
            'savings': 'Savings/Investment CONTRIBUTION', 'misc': 'Miscellaneous Expenses'
        }
        exp_data = [["Expense Category", "Amount"]]
        total_exp = 0
        for k, label in exp_cats.items():
            amt = profile.expenses.get(k, 0)
            if amt > 0:
                exp_data.append([label, format_currency(amt)])
                total_exp += amt
        exp_data.append(["TOTAL ANNUAL EXPENSES", format_currency(total_exp)])
        add_table("1.5 Annual Expenses", exp_data)

        # 1.6 Assets
        ast_map = {'land': 'Land & Building', 'inv': 'Investments', 'cash': 'Cash at Bank', 'retirement': 'Retirement Savings'}
        ast_data = [["Asset Category", "Amount"]]
        total_ast = 0
        for k, label in ast_map.items():
            v = profile.assets.get(k, 0)
            if v > 0:
                ast_data.append([label, format_currency(v)])
                total_ast += v
        ast_data.append(["TOTAL ASSETS", format_currency(total_ast)])
        add_table("1.6 Assets", ast_data)

        # 1.7 Liabilities
        lib_map = {'personal': 'Personal Loan', 'cc': 'Credit Card', 'hb': 'Home/Building Loan'}
        lib_data = [["Liability Category", "Amount"]]
        total_lib = 0
        for k, label in lib_map.items():
            v = profile.liabilities.get(k, 0)
            if v > 0:
                lib_data.append([label, format_currency(v)])
                total_lib += v
        others = profile.liabilities.get('others', [])
        if isinstance(others, list):
            for other in others:
                amt = other.get('amount', 0) if isinstance(other, dict) else getattr(other, 'amount', 0)
                if amt > 0:
                    label = other.get('label', 'Other') if isinstance(other, dict) else getattr(other, 'label', 'Other')
                    lib_data.append([label, format_currency(amt)])
                    total_lib += amt
        lib_data.append(["TOTAL LIABILITIES", format_currency(total_lib)])
        add_table("1.7 Liabilities", lib_data)

        # 2. Net Worth
        add_table("2. Net Worth Summary", [
            ["Particulars", "Value"],
            ["Total Assets", format_currency(total_ast)],
            ["Total Liabilities", format_currency(total_lib)],
            ["NET WORTH", format_currency(total_ast - total_lib)]
        ])

        # 3. Insurance
        ins = profile.insurance
        add_table("3. Insurance Coverage", [
            ["Type", "Coverage", "Premium"],
            ["Life", format_currency(ins.get('life_cover')), format_currency(ins.get('life_premium'))],
            ["Medical", format_currency(ins.get('med_cover')), format_currency(ins.get('med_premium'))],
            ["Vehicle", format_currency(ins.get('veh_cover')), format_currency(ins.get('veh_premium'))]
        ])

        # 4. HLV
        hlv = result.hlv_data
        add_table("4. Human Life Value Analysis", [
            ["Method", "Gross HLV", "Additional Cover Needed"],
            ["Income Method", format_currency(hlv.get('hlv_income_method')), format_currency(hlv.get('additional_life_cover_needed_income'))],
            ["Expense Method", format_currency(hlv.get('hlv_expense_method')), format_currency(hlv.get('additional_life_cover_needed_expense'))]
        ])

        # 6. Retirement
        ret = result.calculations
        add_table("6. Retirement Corpus Analysis", [
            ["Particulars", "Value"],
            ["Corpus Needed", format_currency(ret.get('retirement_corpus_at_retirement'))],
            ["Existing Savings FV", format_currency(ret.get('future_value_existing_savings'))],
            ["Net Corpus Needed", format_currency(ret.get('net_retirement_corpus_needed'))],
            ["Monthly Investment", format_currency(ret.get('monthly_investment_retirement'))]
        ])

        # 7. Cash Flow
        if result.cash_flow_analysis:
            cf_data = [["Year", "Age", "Opening Bal", "Growth", "Withdrawal", "Closing Bal"]]
            for row in result.cash_flow_analysis:
                cf_data.append([str(row['year']), str(row['retirement_age_year']), format_currency(row['opening_balance']), 
                                format_currency(row['investment_growth']), format_currency(row['annual_withdrawal']), format_currency(row['closing_balance'])])
            add_table("7. Retirement Cash Flow Analysis", cf_data)

        # 10. Summary
        add_table("10. Monthly Investment Summary", [
            ["Goal", "Monthly Investment"],
            ["Retirement", format_currency(ret.get('monthly_investment_retirement'))],
            ["Education", format_currency(ret.get('monthly_investment_education'))],
            ["Marriage", format_currency(ret.get('monthly_investment_marriage'))],
            ["TOTAL (Income Method)", format_currency(ret.get('total_monthly_investment_income'))]
        ])

        # 12. Health Score
        score_details = result.calculations.get('financial_health_score_details', [])
        if score_details:
            score_data = [["Component", "Status", "Points"]]
            for comp, stat, pts in score_details:
                score_data.append([comp, str(stat), str(pts)])
            score_data.append(["TOTAL SCORE", "", f"{result.financial_health_score}/100"])
            add_table("12. Financial Health Score", score_data)

        # 13. Conclusion
        if not profile.exclude_ai and result.ai_analysis and 'overall_conclusion' in result.ai_analysis:
            doc.add_heading("13. Overall Conclusion", level=1)
            conc = re.sub(r'<[^>]*>', '', result.ai_analysis['overall_conclusion'])
            doc.add_paragraph(conc)

        doc.add_heading("14. Disclaimer", level=1)
        doc.add_paragraph(profile.disclaimer_text or "Disclaimer content...")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
