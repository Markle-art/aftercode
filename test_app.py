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


def test_investigator_blocks_failed_checks():
    response = client.post(
        "/api/agents/investigator",
        json={
            "commit": "demo-commit-001",
            "checks": [
                {
                    "name": "pytest",
                    "status": "passed",
                    "evidence": "All tests passed.",
                },
                {
                    "name": "semgrep",
                    "status": "failed",
                    "evidence": "A security finding was detected.",
                },
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["recommendation"] == "blocked"
    assert result["summary"]["passed"] == 1
    assert result["summary"]["failed"] == 1
    assert result["release_approved"] is False


def test_investigator_keeps_missing_checks_pending():
    response = client.post(
        "/api/agents/investigator",
        json={
            "commit": "demo-commit-002",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "dependency-audit", "status": "not_run"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["recommendation"] == "pending"
    assert result["summary"]["not_run"] == 1
    assert result["release_approved"] is False
