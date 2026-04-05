"""
Client Registration Blank Form Generator — PDF Generation.
"""
import io
import os
from datetime import datetime
from typing import Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def resolve_logo_path(logo_path: Optional[str]) -> Optional[str]:
    """Try multiple strategies to find the logo file on disk."""
    if not logo_path:
        return None
        
    # Strategy 1: Absolute path
    if os.path.isabs(logo_path) and os.path.exists(logo_path):
        return logo_path
        
    # Strategy 2: Relative to CWD
    if os.path.exists(logo_path):
        return os.path.abspath(logo_path)

    # Strategy 3: Relative to backend root
    file_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.abspath(os.path.join(file_dir, '..', '..', '..')) # backend/app/utils/reports/ -> backend/
    joined_path = os.path.join(backend_root, logo_path)
    if os.path.exists(joined_path):
        return joined_path

    # Strategy 4: Try prepending 'uploads/'
    uploads_path = os.path.join(backend_root, 'uploads', logo_path)
    if os.path.exists(uploads_path):
        return uploads_path

    return None


def generate_client_blank_form(
    ia_logo_path: Optional[str] = None,
    ia_name: str = "",
    ia_reg_no: str = ""
) -> io.BytesIO:
    """Generate a professionally styled, grid-based blank Client Registration Form."""
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is not installed.")

    buffer = io.BytesIO()
    # Compact margins for maximum writing space
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle('FormTitle', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=8, textColor=colors.HexColor('#1e293b'), fontName='Helvetica-Bold')
    section_style = ParagraphStyle('FormSection', parent=styles['Normal'], fontSize=11, textColor=colors.white, fontName='Helvetica-Bold')
    label_style = ParagraphStyle('FormLabel', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=10)
    normal_label_style = ParagraphStyle('NormalLabel', parent=styles['Normal'], fontSize=9, fontName='Helvetica', leading=10)

    def add_section_header(text):
        data = [[Paragraph(text.upper(), section_style)]]
        t = Table(data, colWidths=[535])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e293b')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 4))

    # --- HEADER ---
    header_data = []
    resolved_logo = resolve_logo_path(ia_logo_path)
    if resolved_logo:
        try:
            logo = Image(resolved_logo, width=0.8*inch, height=0.8*inch)
            header_data.append([logo, Paragraph("CLIENT REGISTRATION FORM", title_style), ""])
        except Exception:
            header_data.append(["", Paragraph("CLIENT REGISTRATION FORM", title_style), ""])
    else:
        header_data.append(["", Paragraph("CLIENT REGISTRATION FORM", title_style), ""])
    
    t_header = Table(header_data, colWidths=[80, 375, 80])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(t_header)
    elements.append(Spacer(1, 10))

    # Advisor Info Grid
    info_data = [
        [Paragraph("Advisor Name:", label_style), Paragraph(ia_name, normal_label_style), Paragraph("Advisor ID:", label_style), Paragraph(ia_reg_no, normal_label_style)],
        [Paragraph("Client Code:", label_style), "", Paragraph("Date:", label_style), datetime.now().strftime("%d-%m-%Y")]
    ]
    t_info = Table(info_data, colWidths=[110, 230, 90, 105], rowHeights=25)
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (1,0), (1,0), 0.5, colors.black),
        ('LINEBELOW', (3,0), (3,0), 0.5, colors.black),
        ('LINEBELOW', (1,1), (1,1), 0.5, colors.black),
        ('LINEBELOW', (3,1), (3,1), 0.5, colors.black),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 5))

    # 1. PERSONAL INFORMATION
    add_section_header("1. Personal Details")
    personal_data = [
        [Paragraph("Full Name:", label_style), "", Paragraph("DOB:", label_style), ""],
        [Paragraph("Gender:", label_style), "", Paragraph("Marital Status:", label_style), ""],
        [Paragraph("PAN Number:", label_style), "", Paragraph("Aadhar No:", label_style), ""],
        [Paragraph("Nationality:", label_style), "", Paragraph("Passport No:", label_style), ""],
        [Paragraph("CKYC Number:", label_style), "", Paragraph("CKYC Verified:", label_style), "Yes / No"],
        [Paragraph("Occupation:", label_style), "", "", ""],
        [Paragraph("Father's Name:", label_style), "", "", ""],
        [Paragraph("Mother's Name:", label_style), "", "", ""],
        [Paragraph("Contact Number:", label_style), "", Paragraph("Email ID:", label_style), ""],
        [Paragraph("Residential Status:", label_style), "", Paragraph("Tax Residency:", label_style), ""],
        [Paragraph("PEP Status:", label_style), "", "", ""],
        [Paragraph("Permanent Address:", label_style), "", "", ""],
        ["", "", "", ""]
    ]
    t_personal = Table(personal_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_personal.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        # Row 0: Full Name takes cols 1 and 2, but DOB is in col 2. Mistake in original code.
        # Fixed: Spanning only where columns are explicitly empty.
        ('SPAN', (1,5), (3,5)), ('SPAN', (1,6), (3,6)), ('SPAN', (1,7), (3,7)),
        ('SPAN', (1,10), (3,10)), ('SPAN', (1,11), (3,11)), ('SPAN', (1,12), (3,12)),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_personal)
    elements.append(Spacer(1, 10))

    # 2. FAMILY DETAILS
    add_section_header("2. Family / Spouse Details")
    family_data = [
        [Paragraph("Spouse Name:", label_style), "", Paragraph("Spouse DOB:", label_style), ""],
        [Paragraph("Nominee Name:", label_style), "", Paragraph("Relationship:", label_style), ""]
    ]
    t_family = Table(family_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_family.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_family)
    elements.append(Spacer(1, 10))

    # 3. FINANCIAL INFORMATION
    add_section_header("3. Financial Information")
    financial_data = [
        [Paragraph("Annual Income:", label_style), "Rs.", Paragraph("Net Worth:", label_style), "Rs."],
        [Paragraph("Income Source:", label_style), "", Paragraph("FATCA Status:", label_style), ""],
        [Paragraph("Portfolio Value:", label_style), "Rs.", "", ""],
        [Paragraph("Portfolio Composition:", label_style), "", "", ""]
    ]
    t_financial = Table(financial_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_financial.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (1,2), (3,2)), ('SPAN', (1,3), (3,3)),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_financial)
    elements.append(Spacer(1, 10))

    # 4. BANKING & TRADING DETAILS
    add_section_header("4. Banking & Trading Details")
    banking_data = [
        [Paragraph("Bank Name:", label_style), "", Paragraph("Branch:", label_style), ""],
        [Paragraph("Account Number:", label_style), "", Paragraph("IFSC Code:", label_style), ""],
        [Paragraph("Demat A/c No:", label_style), "", Paragraph("Trading A/c:", label_style), ""]
    ]
    t_banking = Table(banking_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_banking.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_banking)
    elements.append(Spacer(1, 10))

    # 5. INVESTMENT PROFILE
    add_section_header("5. Investment Profile")
    investment_data = [
        [Paragraph("Risk Profile:", label_style), "", Paragraph("Exp (Years):", label_style), ""],
        [Paragraph("Horizon:", label_style), "", Paragraph("Liquidity Needs:", label_style), ""],
        [Paragraph("Objectives:", label_style), "", "", ""],
        ["", "", "", ""]
    ]
    t_investment = Table(investment_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_investment.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (1,2), (3,2)), ('SPAN', (1,3), (3,3)),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_investment)
    elements.append(Spacer(1, 10))

    # 6. ADVISOR & OTHER DETAILS
    add_section_header("6. Advisor & Other Details")
    other_data = [
        [Paragraph("Previous Advisor:", label_style), "", Paragraph("Referral:", label_style), ""],
        [Paragraph("Declaration Date:", label_style), "", Paragraph("Signed (Y/N):", label_style), ""]
    ]
    t_other = Table(other_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_other.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_other)
    elements.append(Spacer(1, 10))

    # 7. FOR OFFICE USE ONLY
    add_section_header("7. For Office Use Only (Internal)")
    ipv_data = [
        [Paragraph("IPV Done By:", label_style), "", Paragraph("Designation:", label_style), ""],
        [Paragraph("IPV Date:", label_style), "", Paragraph("Signature:", label_style), ""]
    ]
    t_ipv = Table(ipv_data, colWidths=[110, 185, 90, 150], rowHeights=24)
    t_ipv.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5)
    ]))
    elements.append(t_ipv)
    elements.append(Spacer(1, 15))

    # 8. DOCUMENTS ATTACHED
    add_section_header("8. Documents Attached")
    doc_data = [
        [Paragraph("[  ]  PAN Card", normal_label_style), Paragraph("[  ]  Aadhaar Card", normal_label_style)],
        [Paragraph("[  ]  Address Proof (Utility/Rent)", normal_label_style), Paragraph("[  ]  Bank Proof (Cheque/Stmt)", normal_label_style)],
        [Paragraph("[  ]  Income Proof (Last 6 Months)", normal_label_style), Paragraph("[  ]  Photographs (2 Nos)", normal_label_style)],
        [Paragraph("[  ]  Signed Agreement", normal_label_style), Paragraph("[  ]  Signature", normal_label_style)]
    ]
    t_docs = Table(doc_data, colWidths=[265, 265], rowHeights=22)
    t_docs.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (10,0), (-1,-1), 5)
    ]))
    elements.append(t_docs)
    elements.append(Spacer(1, 15))

    # 9. SIGNATURES
    add_section_header("9. Declarations & Signatures")
    elements.append(Spacer(1, 10))
    declaration_text = (
        "I hereby declare that the particulars provided above are true and correct to the best of my "
        "knowledge and belief, and I undertake to inform the Advisor of any changes therein immediately. "
        "I understand that in case any of the above information is found to be false, untrue, misleading, "
        "or misrepresenting, I may be held responsible for the same."
    )
    elements.append(Paragraph(declaration_text, normal_label_style))
    elements.append(Spacer(1, 40))
    
    sig_data = [
        ["__________________________", "__________________________"],
        ["Client Signature", "Advisor Signature"],
        ["Date: ___________", "Date: ___________"]
    ]
    sig_table = Table(sig_data, colWidths=[250, 250])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 20),
    ]))
    elements.append(sig_table)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("STRICTLY CONFIDENTIAL - Client Registration Document", ParagraphStyle('Footer', alignment=1, fontSize=7, textColor=colors.grey)))

    doc.build(elements)
    buffer.seek(0)
    return buffer
