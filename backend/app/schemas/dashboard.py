from pydantic import BaseModel
from typing import List, Dict, Optional

class EngagementDistribution(BaseModel):
    High: int
    Medium: int
    Low: int

class ScoreDistributionItem(BaseModel):
    bucket: str
    count: int

class ChannelEffectiveness(BaseModel):
    Email: float
    Website: float
    Webinar: float
    Veeva: float

class ChannelAllocation(BaseModel):
    Email: float
    Website: float
    Webinar: float
    Veeva: float

class DashboardResponse(BaseModel):
    total_hcps: int
    high_engagement: int
    medium_engagement: int
    low_engagement: int
    average_engagement_score: float
    engagement_distribution: EngagementDistribution
    score_distribution: List[ScoreDistributionItem]
    channel_effectiveness: ChannelEffectiveness
    channel_allocation: ChannelAllocation
    last_updated: str

class HealthResponse(BaseModel):
    status: str
