import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.db.database import get_db
from fastapi import HTTPException

client = TestClient(app)

def mock_get_hcp_by_id_success(db, hcp_id):
    return {
        "hcp_id": hcp_id,
        "name": "John Doe",
        "specialty": "Cardiology",
        "hybrid_engagement_score": 85.5,
        "engagement_level": "High",
        "email_probability": 0.9,
        "next_best_channel": "Email"
    }

def mock_get_hcp_by_id_not_found(db, hcp_id):
    raise HTTPException(status_code=404, detail="HCP not found")

def test_get_hcp_success(monkeypatch):
    import app.api.hcps
    monkeypatch.setattr(app.api.hcps, "get_hcp_by_id", mock_get_hcp_by_id_success)
    app.dependency_overrides[get_db] = lambda: MagicMock()

    response = client.get("/api/hcps/HCP123")
    assert response.status_code == 200
    data = response.json()
    assert data["hcp_id"] == "HCP123"
    assert data["name"] == "John Doe"
    assert data["hybrid_engagement_score"] == 85.5

def test_get_hcp_not_found(monkeypatch):
    import app.api.hcps
    monkeypatch.setattr(app.api.hcps, "get_hcp_by_id", mock_get_hcp_by_id_not_found)
    app.dependency_overrides[get_db] = lambda: MagicMock()

    response = client.get("/api/hcps/UNKNOWN")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "HCP not found"
