from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db.models import ModelOutput, HCPProfile
from app.schemas.dashboard import (
    DashboardResponse,
    EngagementDistribution,
    ScoreDistributionItem,
    ChannelEffectiveness,
    ChannelAllocation
)
from datetime import datetime

def get_dashboard_data(db: Session) -> DashboardResponse:
    # 1. Total HCPs (from ModelOutput, as we only care about HCPs with model outputs)
    total_hcps = db.query(func.count(ModelOutput.hcp_id)).scalar() or 0

    if total_hcps == 0:
        # Return empty/default response
        return DashboardResponse(
            total_hcps=0,
            high_engagement=0,
            medium_engagement=0,
            low_engagement=0,
            average_engagement_score=0.0,
            engagement_distribution=EngagementDistribution(High=0, Medium=0, Low=0),
            score_distribution=[],
            channel_effectiveness=ChannelEffectiveness(Email=0.0, Website=0.0, Webinar=0.0, Veeva=0.0),
            channel_allocation=ChannelAllocation(Email=0.0, Website=0.0, Webinar=0.0, Veeva=0.0),
            last_updated=datetime.utcnow().isoformat()
        )

    # 2 & 3. Engagement Levels
    engagement_counts = db.query(
        ModelOutput.engagement_level,
        func.count(ModelOutput.hcp_id)
    ).group_by(ModelOutput.engagement_level).all()

    eng_dist = {"High": 0, "Medium": 0, "Low": 0}
    for level, count in engagement_counts:
        if level in eng_dist:
            eng_dist[level] = count

    # 4. Average Hybrid Engagement Score
    avg_score = db.query(func.avg(ModelOutput.hybrid_engagement_score)).scalar() or 0.0

    # 5. Score Distribution (Buckets)
    # 0-20, 21-40, 41-60, 61-80, 81-100
    score_col = ModelOutput.hybrid_engagement_score
    buckets = db.query(
        case(
            (score_col <= 20, "0-20"),
            (score_col <= 40, "21-40"),
            (score_col <= 60, "41-60"),
            (score_col <= 80, "61-80"),
            else_="81-100"
        ).label("bucket"),
        func.count(ModelOutput.hcp_id)
    ).group_by("bucket").all()

    bucket_counts = {b: 0 for b in ["0-20", "21-40", "41-60", "61-80", "81-100"]}
    for bucket, count in buckets:
        if bucket in bucket_counts:
            bucket_counts[bucket] = count

    score_dist_items = [
        ScoreDistributionItem(bucket=b, count=bucket_counts[b])
        for b in ["0-20", "21-40", "41-60", "61-80", "81-100"]
    ]

    # 6. Channel Effectiveness (Averages)
    avg_probs = db.query(
        func.avg(ModelOutput.email_probability),
        func.avg(ModelOutput.website_probability),
        func.avg(ModelOutput.webinar_probability),
        func.avg(ModelOutput.veeva_probability)
    ).first()

    email_avg = avg_probs[0] or 0.0
    website_avg = avg_probs[1] or 0.0
    webinar_avg = avg_probs[2] or 0.0
    veeva_avg = avg_probs[3] or 0.0

    # 7. Channel Allocation (Model-Driven)
    total_prob = email_avg + website_avg + webinar_avg + veeva_avg
    if total_prob > 0:
        email_alloc = email_avg / total_prob
        website_alloc = website_avg / total_prob
        webinar_alloc = webinar_avg / total_prob
        veeva_alloc = veeva_avg / total_prob
    else:
        email_alloc = website_alloc = webinar_alloc = veeva_alloc = 0.0

    # 8. Last Updated
    last_updated_record = db.query(func.max(HCPProfile.updated_at)).scalar()
    last_updated = last_updated_record.isoformat() if last_updated_record else datetime.utcnow().isoformat()

    return DashboardResponse(
        total_hcps=total_hcps,
        high_engagement=eng_dist["High"],
        medium_engagement=eng_dist["Medium"],
        low_engagement=eng_dist["Low"],
        average_engagement_score=avg_score,
        engagement_distribution=EngagementDistribution(**eng_dist),
        score_distribution=score_dist_items,
        channel_effectiveness=ChannelEffectiveness(
            Email=email_avg, Website=website_avg, Webinar=webinar_avg, Veeva=veeva_avg
        ),
        channel_allocation=ChannelAllocation(
            Email=email_alloc, Website=website_alloc, Webinar=webinar_alloc, Veeva=veeva_alloc
        ),
        last_updated=last_updated
    )
