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
        
        responses = [
            ["Q1. Interest Choice:", assessment.q1_interest_choice],
            ["Q3. Probability Bet:", assessment.q3_probability_bet],
            ["Q4. Portfolio Choice:", assessment.q4_portfolio_choice],
            ["Q5. Loss Behavior:", assessment.q5_loss_behavior],
            ["Q6. Market Reaction:", assessment.q6_market_reaction],
            ["Q7. Fund Selection:", assessment.q7_fund_selection],
            ["Q8. Experience Level:", assessment.q8_experience_level],
            ["Q9. Time Horizon:", assessment.q9_time_horizon],
            ["Q10. Net Worth:", assessment.q10_net_worth],
            ["Q11. Age Range:", assessment.q11_age_range],
            ["Q12. Income Range:", assessment.q12_income_range],
            ["Q13. Expense Range:", assessment.q13_expense_range],
            ["Q14. Dependents:", assessment.q14_dependents],
            ["Q15. Active Loan:", assessment.q15_active_loan],
            ["Q16. Investment Objective:", assessment.q16_investment_objective]
        ]
        
        resp_table = Table(responses, colWidths=[2.5*inch, 4*inch])
        resp_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.2, colors.lightgrey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(resp_table)
        
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
