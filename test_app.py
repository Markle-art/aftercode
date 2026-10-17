from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_root_describes_aftercode():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "AfterCode"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_release_is_not_approved_without_verification():
    response = client.get("/release-readiness")
    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["decision"] == "pending"
