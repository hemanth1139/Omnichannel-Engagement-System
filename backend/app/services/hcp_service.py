from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db.models import HCPProfile, ModelOutput
from app.schemas.hcp import HcpDetailResponse
import io
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    pass # Handled in requirements

def get_hcp_by_id(db: Session, hcp_id: str) -> HcpDetailResponse:
    record = (
        db.query(HCPProfile, ModelOutput)
        .outerjoin(ModelOutput, HCPProfile.hcp_id == ModelOutput.hcp_id)
        .filter(HCPProfile.hcp_id == hcp_id)
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="HCP not found")

    profile, model_out = record

    return HcpDetailResponse(
        hcp_id=profile.hcp_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        specialty=profile.specialty,
        sub_specialty=profile.sub_specialty,
        organization_type=profile.organization_type,
        city=profile.city,
        state=profile.state,
        country=profile.country,
        hcp_status=profile.hcp_status,
        preferred_language=profile.preferred_language,
        
        # Model Outputs (Handle cases where model output might be missing)
        historical_engagement_score=model_out.historical_engagement_score if model_out else None,
        predicted_engagement_score=model_out.predicted_engagement_score if model_out else None,
        hybrid_engagement_score=model_out.hybrid_engagement_score if model_out else None,
        engagement_level=model_out.engagement_level if model_out else None,
        
        email_probability=model_out.email_probability if model_out else None,
        website_probability=model_out.website_probability if model_out else None,
        webinar_probability=model_out.webinar_probability if model_out else None,
        sales_rep_probability=model_out.sales_rep_probability if model_out else None,
        
        next_best_channel=model_out.next_best_channel if model_out else None,
        recommended_reason=model_out.recommended_reason if model_out else None,
    )

from typing import List
from sqlalchemy import or_

def search_hcps(db: Session, query: str = None, skip: int = 0, limit: int = 50) -> List[HcpDetailResponse]:
    q = db.query(HCPProfile, ModelOutput).outerjoin(ModelOutput, HCPProfile.hcp_id == ModelOutput.hcp_id)
    
    if query:
        search_term = f"%{query}%"
        q = q.filter(
            or_(
                HCPProfile.first_name.ilike(search_term),
                HCPProfile.last_name.ilike(search_term),
                HCPProfile.hcp_id.ilike(search_term),
                HCPProfile.specialty.ilike(search_term)
            )
        )
    
    records = q.order_by(HCPProfile.hcp_id.asc()).offset(skip).limit(limit).all()
    results = []
    for profile, model_out in records:
        results.append(HcpDetailResponse(
            hcp_id=profile.hcp_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            specialty=profile.specialty,
            sub_specialty=profile.sub_specialty,
            organization_type=profile.organization_type,
            city=profile.city,
            state=profile.state,
            country=profile.country,
            hcp_status=profile.hcp_status,
            preferred_language=profile.preferred_language,
            historical_engagement_score=model_out.historical_engagement_score if model_out else None,
            predicted_engagement_score=model_out.predicted_engagement_score if model_out else None,
            hybrid_engagement_score=model_out.hybrid_engagement_score if model_out else None,
            engagement_level=model_out.engagement_level if model_out else None,
            email_probability=model_out.email_probability if model_out else None,
            website_probability=model_out.website_probability if model_out else None,
            webinar_probability=model_out.webinar_probability if model_out else None,
            sales_rep_probability=model_out.sales_rep_probability if model_out else None,
            next_best_channel=model_out.next_best_channel if model_out else None,
            recommended_reason=model_out.recommended_reason if model_out else None,
        ))
    return results

def generate_all_hcps_pdf(db: Session) -> io.BytesIO:
    hcps = search_hcps(db, query=None, skip=0, limit=10000)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    elements = []
    
    styles = getSampleStyleSheet()
    title = Paragraph("HCP Directory Report", styles['Title'])
    elements.append(title)
    
    # Define table data
    data = [['HCP ID', 'Name', 'Engagement Score', 'Next Best Channel']]
    
    for hcp in hcps:
        name = f"{hcp.first_name or ''} {hcp.last_name or ''}".strip()
        score = f"{hcp.hybrid_engagement_score:.0f}%" if hcp.hybrid_engagement_score else "N/A"
        nbc = hcp.next_best_channel or "N/A"
        
        data.append([hcp.hcp_id, name, score, nbc])
        
    table = Table(data, repeatRows=1)
    
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#061a3a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])
    table.setStyle(style)
    
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f5f9fc")
        else:
            bg_color = colors.white
        table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), bg_color)]))

    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer

def generate_single_hcp_pdf(db: Session, hcp_id: str) -> io.BytesIO:
    hcp = get_hcp_by_id(db, hcp_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = styles['Title']
    title_style.textColor = colors.HexColor("#061a3a")
    
    h2_style = styles['Heading2']
    h2_style.textColor = colors.HexColor("#00c2cb")
    h2_style.spaceBefore = 15
    h2_style.spaceAfter = 10
    
    normal = styles['Normal']
    normal.fontSize = 11
    normal.leading = 14
    
    # 1. Header
    name = f"{hcp.first_name or ''} {hcp.last_name or ''}".strip()
    elements.append(Paragraph(name, title_style))
    elements.append(Paragraph(f"<b>HCP ID:</b> {hcp.hcp_id} | <b>Specialty:</b> {hcp.specialty}", normal))
    elements.append(Paragraph("<br/>", normal))
    
    # 2. Profile Information
    elements.append(Paragraph("Profile Information", h2_style))
    profile_data = [
        ['Organization Type:', hcp.organization_type or 'N/A'],
        ['Location:', f"{hcp.city or ''}, {hcp.state or ''}, {hcp.country or ''}".strip(', ')],
        ['Status:', hcp.hcp_status or 'N/A'],
        ['Preferred Language:', hcp.preferred_language or 'N/A']
    ]
    t1 = Table(profile_data, colWidths=[150, 350])
    t1.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t1)
    
    # 3. Engagement Summary
    elements.append(Paragraph("<br/>", normal))
    elements.append(Paragraph("Engagement Summary", h2_style))
    
    score = f"{hcp.hybrid_engagement_score:.0f}%" if hcp.hybrid_engagement_score else "N/A"
    eng_data = [
        ['Engagement Level:', hcp.engagement_level or 'N/A'],
        ['Hybrid Engagement Score:', score],
        ['Historical Score:', f"{hcp.historical_engagement_score or 0:.0f}%"],
        ['Predicted Score:', f"{hcp.predicted_engagement_score or 0:.0f}%"]
    ]
    t2 = Table(eng_data, colWidths=[150, 350])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t2)
    
    # 4. Channel Probabilities
    elements.append(Paragraph("<br/>", normal))
    elements.append(Paragraph("Channel Probabilities", h2_style))
    
    chan_data = [
        ['Email', f"{hcp.email_probability or 0:.0f}%"],
        ['Website', f"{hcp.website_probability or 0:.0f}%"],
        ['Webinar', f"{hcp.webinar_probability or 0:.0f}%"],
        ['Sales Rep', f"{hcp.sales_rep_probability or 0:.0f}%"]
    ]
    t3 = Table(chan_data, colWidths=[150, 100])
    t3.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t3)
    
    # 5. Next Best Channel
    elements.append(Paragraph("<br/>", normal))
    elements.append(Paragraph("Next Best Channel Recommendation", h2_style))
    elements.append(Paragraph(f"<b>Channel:</b> {hcp.next_best_channel or 'N/A'}", normal))
    elements.append(Paragraph(f"<b>Reason:</b> {hcp.recommended_reason or 'N/A'}", normal))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
