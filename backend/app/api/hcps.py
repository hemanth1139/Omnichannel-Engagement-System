from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.schemas.hcp import HcpDetailResponse
from app.services.hcp_service import get_hcp_by_id, search_hcps

router = APIRouter()

@router.get("/api/hcps", response_model=List[HcpDetailResponse])
def get_hcps(query: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Search HCPs by query (matches name, id, or specialty).
    """
    return search_hcps(db, query)

@router.get("/api/hcps/{hcp_id}", response_model=HcpDetailResponse)
def get_hcp_detail(hcp_id: str, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific HCP.
    """
    return get_hcp_by_id(db, hcp_id)
