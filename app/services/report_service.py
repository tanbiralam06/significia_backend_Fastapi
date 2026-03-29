import os
import uuid
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image

from app.models.risk_profile import RiskAssessment
from app.models.client import ClientProfile
from app.models.ia_master import IAMaster
from sqlalchemy.orm import Session
from sqlalchemy import select
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.services.questionnaire_constants import QUESTIONNAIRE_DATA

class ReportService:
    @staticmethod
    def generate_risk_profile_pdf(db: Session, assessment_id: uuid.UUID) -> BytesIO:
        # 1. Fetch Assessment and related data
        assessment = db.execute(
            select(RiskAssessment).where(RiskAssessment.id == assessment_id)
        ).scalar_one_or_none()
        
        if not assessment:
            raise ValueError("Assessment not found")
            
        client = assessment.client
        
        # Fetch IA details based on advisor name or reg number
        # Note: In the standalone, it used ia_registration_number. 
        # In current models, we look up IAMaster.
        ia = db.execute(
            select(IAMaster).where(IAMaster.ia_registration_number == assessment.client.advisor_name)
        ).scalar_one_or_none()
        # Fallback if IA not found by name
        if not ia:
            # Maybe try filtering by client if there was a direct link, but assuming global IA master for now
            ia = db.execute(select(IAMaster)).first()
            if ia: ia = ia[0]

        buffer = BytesIO()
        
        # 2. Setup Document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter, 
            topMargin=1.2*inch,
            bottomMargin=0.7*inch, 
            leftMargin=0.5*inch, 
            rightMargin=0.5*inch
        )
        
        story = []
        styles = getSampleStyleSheet()

        # Custom styles (Ported from risk_profile.py)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1e3c72'),
            spaceAfter=20,
            alignment=1,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2a5298'),
            spaceAfter=12,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'NormalCustom',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=4,
            fontName='Helvetica'
        )

        bold_style = ParagraphStyle(
            'BoldCustom',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )

        preformatted_style = ParagraphStyle(
            'PreformattedStyle',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Courier',
            leading=10,
            spaceAfter=2,
            leftIndent=0,
            rightIndent=0,
            alignment=0
        )

        # 3. Add Header with Logo
        if ia and ia.ia_logo_path and os.path.exists(ia.ia_logo_path):
            try:
                logo = Image(ia.ia_logo_path, width=1.5*inch, height=0.75*inch)
                header_data = [[logo, Paragraph("RISK PROFILING REPORT", title_style)]]
                header_table = Table(header_data, colWidths=[2*inch, 5*inch])
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (0,0), 'LEFT'),
                    ('ALIGN', (1,0), (1,0), 'CENTER'),
                ]))
                story.append(header_table)
            except:
                story.append(Paragraph("RISK PROFILING REPORT", title_style))
        else:
            story.append(Paragraph("RISK PROFILING REPORT", title_style))
        
        story.append(Spacer(1, 10))

        # 4. Result Summary Section
        story.append(Paragraph("ASSESSMENT SUMMARY", heading_style))
        summary_data = [
            ["Client Name:", client.client_name],
            ["Client Code:", client.client_code],
            ["Date of Assessment:", assessment.assessment_timestamp.strftime("%Y-%m-%d %H:%M")],
            ["Total Score:", str(assessment.calculated_score)],
            ["Risk Category:", assessment.assigned_risk_tier]
        ]
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # 5. Questionnaire Responses
        story.append(Paragraph("QUESTIONNAIRE RESPONSES", heading_style))
        
        for q_id, q_data in QUESTIONNAIRE_DATA.items():
            story.append(Paragraph(f"<b>{q_id.upper()}. {q_data['title']}</b>", normal_style))
            story.append(Paragraph(q_data['question'], normal_style))
            
            # Handle Q2 (Factors) specifically
            if q_id == 'q2':
                q2_answers = assessment.q2_importance_factors
                table_data = [["Factor", "Importance"]]
                for f_code, f_name in q_data['factors'].items():
                    ans_code = q2_answers.get(f_code, "-")
                    ans_text = q_data['options'].get(ans_code, ans_code)
                    table_data.append([f_name, Paragraph(f"<b>{ans_text}</b>", bold_style)])
                
                q2_table = Table(table_data, colWidths=[3.5*inch, 2.5*inch])
                q2_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.2, colors.lightgrey),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                    ('PADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(q2_table)
            else:
                # Standard questions - mapping q_id to model field name
                field_map = {
                    'q1': 'q1_interest_choice',
                    'q3': 'q3_probability_bet',
                    'q4': 'q4_portfolio_choice',
                    'q5': 'q5_loss_behavior',
                    'q6': 'q6_market_reaction',
                    'q7': 'q7_fund_selection',
                    'q8': 'q8_experience_level',
                    'q9': 'q9_time_horizon',
                    'q10': 'q10_net_worth',
                    'q11': 'q11_age_range',
                    'q12': 'q12_income_range',
                    'q13': 'q13_expense_range',
                    'q14': 'q14_dependents',
                    'q15': 'q15_active_loan',
                    'q16': 'q16_investment_objective'
                }
                field_name = field_map.get(q_id, q_id)
                selected_val = getattr(assessment, field_name, "N/A")
                
                options_str = ""
                for opt_code, opt_text in q_data['options'].items():
                    is_selected = opt_code.lower() == str(selected_val).lower()
                    prefix = f"<b>[✓]</b> " if is_selected else "[  ] "
                    text_color = "#006400" if is_selected else "#000000" # Dark Green for selected
                    options_str += f"<font color='{text_color}'>{prefix}{opt_code}. {opt_text}</font><br/>"
                
                story.append(Paragraph(options_str, ParagraphStyle('Options', parent=normal_style, leftIndent=20, leading=12)))
            
            story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 15))
        
        # 6. Recommendation and Notes
        story.append(Paragraph("ADVISOR RECOMMENDATION", heading_style))
        story.append(Paragraph(assessment.tier_recommendation or "No recommendation provided.", normal_style))
        
        if assessment.discussion_notes:
            story.append(Paragraph("DISCUSSION NOTES", heading_style))
            story.append(Paragraph(assessment.discussion_notes, normal_style))

        if assessment.disclaimer_text:
            story.append(Spacer(1, 20))
            story.append(Paragraph("DISCLAIMER", bold_style))
            story.append(Paragraph(assessment.disclaimer_text, ParagraphStyle('Disc', parent=normal_style, fontSize=7, textColor=colors.grey)))

        # 7. Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_risk_profile_docx(db: Session, assessment_id: uuid.UUID) -> BytesIO:
        # 1. Fetch Data
        assessment = db.execute(
            select(RiskAssessment).where(RiskAssessment.id == assessment_id)
        ).scalar_one_or_none()
        
        if not assessment:
            raise ValueError("Assessment not found")
            
        client = assessment.client
        ia = db.execute(
            select(IAMaster).where(IAMaster.ia_registration_number == assessment.client.advisor_name)
        ).scalar_one_or_none()
        if not ia:
            ia = db.execute(select(IAMaster)).first()
            if ia: ia = ia[0]

        # 2. Setup DOCX
        doc = Document()
        
        # Styles
        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(10)

        # 3. Header
        header = doc.add_heading('RISK PROFILING REPORT', 0)
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 4. Summary Table
        doc.add_heading('ASSESSMENT SUMMARY', level=1)
        table = doc.add_table(rows=5, cols=2)
        table.style = 'Table Grid'
        
        summary_rows = [
            ("Client Name:", client.client_name),
            ("Client Code:", client.client_code),
            ("Date of Assessment:", assessment.assessment_timestamp.strftime("%Y-%m-%d %H:%M")),
            ("Total Score:", str(assessment.calculated_score)),
            ("Risk Category:", assessment.assigned_risk_tier)
        ]
        
        for i, (label, value) in enumerate(summary_rows):
            table.cell(i, 0).text = label
            table.cell(i, 1).text = value
            table.cell(i, 0).paragraphs[0].runs[0].bold = True

        doc.add_paragraph().add_run().add_break()

        # 5. Questionnaire Responses
        doc.add_heading('QUESTIONNAIRE RESPONSES', level=1)
        
        for q_id, q_data in QUESTIONNAIRE_DATA.items():
            p = doc.add_paragraph()
            p.add_run(f"{q_id.upper()}. {q_data['title']}").bold = True
            doc.add_paragraph(q_data['question'])
            
            if q_id == 'q2':
                q2_answers = assessment.q2_importance_factors
                t2 = doc.add_table(rows=1, cols=2)
                t2.style = 'Table Grid'
                hdr_cells = t2.rows[0].cells
                hdr_cells[0].text = 'Factor'
                hdr_cells[1].text = 'Importance'
                
                for f_code, f_name in q_data['factors'].items():
                    ans_code = q2_answers.get(f_code, "-")
                    ans_text = q_data['options'].get(ans_code, ans_code)
                    row_cells = t2.add_row().cells
                    row_cells[0].text = f_name
                    row_cells[1].text = ans_text
                    row_cells[1].paragraphs[0].runs[0].bold = True
            else:
                # Standard questions - mapping q_id to model field name
                field_map = {
                    'q1': 'q1_interest_choice',
                    'q3': 'q3_probability_bet',
                    'q4': 'q4_portfolio_choice',
                    'q5': 'q5_loss_behavior',
                    'q6': 'q6_market_reaction',
                    'q7': 'q7_fund_selection',
                    'q8': 'q8_experience_level',
                    'q9': 'q9_time_horizon',
                    'q10': 'q10_net_worth',
                    'q11': 'q11_age_range',
                    'q12': 'q12_income_range',
                    'q13': 'q13_expense_range',
                    'q14': 'q14_dependents',
                    'q15': 'q15_active_loan',
                    'q16': 'q16_investment_objective'
                }
                field_name = field_map.get(q_id, q_id)
                selected_val = getattr(assessment, field_name, "N/A")

                for opt_code, opt_text in q_data['options'].items():
                    is_selected = opt_code.lower() == str(selected_val).lower()
                    prefix = f"[✓] " if is_selected else "[  ] "
                    option_p = doc.add_paragraph()
                    option_p.paragraph_format.left_indent = Pt(20)
                    run = option_p.add_run(f"{prefix}{opt_code}. {opt_text}")
                    if is_selected:
                        run.bold = True
                        run.font.color.rgb = RGBColor(0, 100, 0) # Dark Green
            
            doc.add_paragraph() # Spacer

        # 6. Recommendation and Notes
        doc.add_heading('ADVISOR RECOMMENDATION', level=1)
        doc.add_paragraph(assessment.tier_recommendation or "No recommendation provided.")
        
        if assessment.discussion_notes:
            doc.add_heading('DISCUSSION NOTES', level=1)
            doc.add_paragraph(assessment.discussion_notes)

        if assessment.disclaimer_text:
            doc.add_paragraph()
            p = doc.add_paragraph()
            run = p.add_run("DISCLAIMER: ")
            run.bold = True
            p.add_run(assessment.disclaimer_text)

        # 7. Save to Buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
