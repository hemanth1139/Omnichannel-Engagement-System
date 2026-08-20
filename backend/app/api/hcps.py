from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.schemas.hcp import HcpDetailResponse
from app.services.hcp_service import get_hcp_by_id, search_hcps, generate_all_hcps_pdf, generate_single_hcp_pdf

router = APIRouter()

@router.get("/api/hcps", response_model=List[HcpDetailResponse])
def get_hcps(query: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Search HCPs by query (matches name, id, or specialty).
    """
    return search_hcps(db, query, skip, limit)

@router.get("/api/hcps/export/pdf")
def export_all_hcps_pdf(db: Session = Depends(get_db)):
    """
    Export all HCPs to a PDF file.
    """
    pdf_buffer = generate_all_hcps_pdf(db)
    return Response(
        content=pdf_buffer.getvalue(), 
        media_type="application/pdf", 
        headers={"Content-Disposition": "attachment; filename=All_HCPs_Report.pdf"}
    )

@router.get("/api/hcps/{hcp_id}/export/pdf")
def export_single_hcp_pdf(hcp_id: str, db: Session = Depends(get_db)):
    """
    Export a specific HCP to a PDF file.
    """
    pdf_buffer = generate_single_hcp_pdf(db, hcp_id)
    return Response(
        content=pdf_buffer.getvalue(), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={hcp_id}_Profile.pdf"}
    )

@router.get("/api/hcps/{hcp_id}", response_model=HcpDetailResponse)
def get_hcp_detail(hcp_id: str, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific HCP.
    """
    return get_hcp_by_id(db, hcp_id)
