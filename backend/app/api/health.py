from fastapi import APIRouter
from app.schemas.dashboard import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "healthy"}
