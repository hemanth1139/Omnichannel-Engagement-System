from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, dashboard, hcps
from app.db.database import engine
from app.db.models import Base

# Auto-create missing tables (like ml_predictions) if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HCP Engagement Intelligence API",
    description="Backend API for the HCP Engagement Intelligence dashboard.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(hcps.router, tags=["HCP"])
