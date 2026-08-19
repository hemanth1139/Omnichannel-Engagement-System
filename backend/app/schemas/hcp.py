from pydantic import BaseModel
from typing import Optional

class HcpDetailResponse(BaseModel):
    hcp_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialty: Optional[str] = None
    sub_specialty: Optional[str] = None
    organization_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    hcp_status: Optional[str] = None
    preferred_language: Optional[str] = None
    
    historical_engagement_score: Optional[float] = None
    predicted_engagement_score: Optional[float] = None
    hybrid_engagement_score: Optional[float] = None
    engagement_level: Optional[str] = None
    
    email_probability: Optional[float] = None
    website_probability: Optional[float] = None
    webinar_probability: Optional[float] = None
    sales_rep_probability: Optional[float] = None
    
    next_best_channel: Optional[str] = None
    recommended_reason: Optional[str] = None
