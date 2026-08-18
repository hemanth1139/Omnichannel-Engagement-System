from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.hcp import HcpDetailResponse
from app.services.hcp_service import get_hcp_by_id

router = APIRouter()

@router.get("/api/hcps/{hcp_id}", response_model=HcpDetailResponse)
def get_hcp_detail(hcp_id: str, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific HCP.
    """
    return get_hcp_by_id(db, hcp_id)
