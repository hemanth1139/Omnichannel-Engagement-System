from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, MetaData
from sqlalchemy.orm import declarative_base, relationship
from app.config import settings

Base = declarative_base()

class HCPProfile(Base):
    __tablename__ = settings.HCP_PROFILE_TABLE_NAME

    hcp_id = Column(String, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    specialty = Column(String)
    sub_specialty = Column(String)
    organization_id = Column(String)
    organization_type = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    region = Column(String)
    hcp_status = Column(String)
    consent_status = Column(String)
    preferred_language = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    model_output = relationship("ModelOutput", back_populates="hcp_profile", uselist=False)

class ModelOutput(Base):
    __tablename__ = settings.MODEL_OUTPUT_TABLE_NAME

    # For strict mapping we assume snake_case columns. If columns literally have spaces in Postgres, 
    # you can rename them like: Column("Historical Engagement Score", Float)
    hcp_id = Column(String, ForeignKey(f"{settings.HCP_PROFILE_TABLE_NAME}.hcp_id"), primary_key=True, index=True)
    historical_engagement_score = Column(Float)
    predicted_engagement_score = Column(Float)
    hybrid_engagement_score = Column(Float)
    engagement_level = Column(String, index=True)
    email_probability = Column(Float)
    website_probability = Column(Float)
    webinar_probability = Column(Float)
    veeva_probability = Column(Float)
    next_best_channel = Column(String, index=True)
    recommendation_reason = Column(String)

    hcp_profile = relationship("HCPProfile", back_populates="model_output")
