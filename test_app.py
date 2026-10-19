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


def test_security_analyst_reports_failed_security_check():
    response = client.post(
        "/api/agents/security-analyst",
        json={
            "commit": "security-demo-001",
            "checks": [
                {
                    "name": "semgrep",
                    "status": "failed",
                    "evidence": "A security rule reported a finding.",
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["assessment"] == "risks_detected"
    assert result["failed_checks"] == 1
    assert result["findings"][0]["risk"] == "high"
    assert result["release_approved"] is False


def test_security_analyst_does_not_treat_missing_scan_as_safe():
    response = client.post(
        "/api/agents/security-analyst",
        json={
            "commit": "security-demo-002",
            "checks": [
                {"name": "dependency-audit", "status": "not_run"}
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["assessment"] == "incomplete"
    assert result["checks_not_run"] == 1
    assert result["release_approved"] is False


def test_release_passport_blocks_failed_check():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "passport-demo-001",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {
                    "name": "semgrep",
                    "status": "failed",
                    "evidence": "A security finding was reported.",
                },
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "blocked"
    assert result["summary"]["failed"] == 1
    assert result["release_approved"] is False
    assert result["human_action_required"] is True


def test_release_passport_keeps_unrun_check_pending():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "passport-demo-002",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "dependency-audit", "status": "not_run"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "pending"
    assert result["summary"]["not_run"] == 1
    assert result["release_approved"] is False


def test_release_passport_requires_human_review_when_checks_pass():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "passport-demo-003",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
                {"name": "dependency-audit", "status": "passed"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "ready_for_human_review"
    assert result["summary"]["passed"] == 3
    assert result["release_approved"] is False
    assert result["human_action_required"] is True
