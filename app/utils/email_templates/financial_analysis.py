"""
Financial Analysis Email Template
───────────────────────────────────
Centralized definition for the default email format when sending
financial analysis reports to clients.
"""

def get_financial_analysis_template(context: dict) -> str:
    """
    Returns the rendered HTML body for Financial Analysis delivery.
    
    Context keys:
        - client_name
        - ia_name
        - ia_reg_no
        - ia_firm_name
        - ia_contact_details
    """
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px;">
        <p>Dear {context.get('client_name', 'Client')},</p>

        <p>Please find attached your Financial Analysis Report, prepared based on the information and assumptions discussed.</p>

        <p>This report provides computational and illustrative financial analysis and does not constitute investment advice, recommendation, or opinion on any investment products, strategies, or asset allocation. Any advisory services, interpretation, or recommendations will be provided separately by the Investment Adviser.</p>

        <p>If you have any questions or require further clarification, please feel free to get in touch.</p>

        <p>Regards,<br>
        <strong>{context.get('ia_name', 'Your Advisor')}</strong><br>
        {context.get('ia_reg_no', '')}<br>
        {context.get('ia_firm_name', '')}<br>
        {context.get('ia_contact_details', '')}</p>

        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        
        <p style="font-size: 11px; color: #777;">
            <strong>Disclaimer:</strong><br>
            This communication is for informational purposes only and is intended solely for the addressee. 
            The attached report is based on inputs and assumptions and is illustrative in nature. 
            The Investment Adviser is solely responsible for any advisory services provided separately. 
            If you are not the intended recipient, please delete this email and notify the sender. 
            Unauthorized use or distribution is prohibited.
        </p>
    </div>
    """

def get_financial_analysis_subject(client_name: str) -> str:
    return f"Financial Analysis Report — {client_name}"
