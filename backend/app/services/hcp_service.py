from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db.models import HCPProfile, ModelOutput
from app.schemas.hcp import HcpDetailResponse

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

    name_parts = [p for p in [profile.first_name, profile.last_name] if p]
    full_name = " ".join(name_parts)

    return HcpDetailResponse(
        hcp_id=profile.hcp_id,
        name=full_name,
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
        veeva_probability=model_out.veeva_probability if model_out else None,
        
        next_best_channel=model_out.next_best_channel if model_out else None,
        recommendation_reason=model_out.recommendation_reason if model_out else None,
    )
