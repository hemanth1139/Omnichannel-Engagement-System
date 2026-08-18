import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.db.database import get_db

client = TestClient(app)

def mock_get_dashboard_data(db):
    return {
        "total_hcps": 100,
        "high_engagement": 20,
        "medium_engagement": 50,
        "low_engagement": 30,
        "average_engagement_score": 60.5,
        "engagement_distribution": {"High": 20, "Medium": 50, "Low": 30},
        "score_distribution": [
            {"bucket": "0-20", "count": 10},
            {"bucket": "21-40", "count": 20},
            {"bucket": "41-60", "count": 30},
            {"bucket": "61-80", "count": 25},
            {"bucket": "81-100", "count": 15}
        ],
        "channel_effectiveness": {"Email": 0.5, "Website": 0.4, "Webinar": 0.3, "Veeva": 0.2},
        "channel_allocation": {"Email": 0.35, "Website": 0.28, "Webinar": 0.21, "Veeva": 0.14},
        "last_updated": "2024-01-01T00:00:00Z"
    }

def test_get_dashboard(monkeypatch):
    import app.api.dashboard
    monkeypatch.setattr(app.api.dashboard, "get_dashboard_data", mock_get_dashboard_data)
    
    # We can override the db dependency just in case, though the mock intercepts the service call
    app.dependency_overrides[get_db] = lambda: MagicMock()

    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hcps"] == 100
    assert data["average_engagement_score"] == 60.5
    assert data["engagement_distribution"]["High"] == 20
    assert data["channel_effectiveness"]["Email"] == 0.5
