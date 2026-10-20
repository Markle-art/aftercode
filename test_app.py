from fastapi.testclient import TestClient

import app as app_module
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


def test_ci_log_investigator_returns_evidence_and_line_number():
    response = client.post(
        "/api/agents/ci-investigator",
        json={
            "log": (
                "Preparing environment\n"
                "FAILED test_app.py::test_health - AssertionError\n"
            )
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["agent"] == "ci-investigator"
    assert result["status"] == "findings_detected"
    assert result["findings"][0]["category"] == "test_failure"
    assert result["findings"][0]["line_number"] == 2
    assert result["human_review_required"] is True


def test_ci_log_investigator_does_not_invent_findings():
    response = client.post(
        "/api/agents/ci-investigator",
        json={"log": "Preparing environment\nDownloading dependencies\n"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "unknown"
    assert result["findings"] == []
    assert result["human_review_required"] is True


def test_ci_log_investigator_rejects_oversized_log():
    response = client.post(
        "/api/agents/ci-investigator",
        json={"log": "x" * 2_000_001},
    )

    assert response.status_code == 422


def test_gitlab_job_investigation_analyzes_retrieved_trace(monkeypatch):
    def fake_trace(job_id):
        assert job_id == 123
        return {
            "job_id": job_id,
            "source": "GitLab job trace",
            "trace": (
                "Preparing environment\n"
                "FAILED test_app.py::test_health - AssertionError\n"
            ),
            "truncated": False,
            "human_review_required": True,
        }

    monkeypatch.setattr(app_module, "gitlab_job_trace", fake_trace)

    response = client.post("/api/agents/ci-investigator/gitlab/123")

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "ci-investigator"
    assert data["job_id"] == 123
    assert data["source"] == "GitLab job trace"
    assert data["trace_truncated"] is False
    assert data["status"] == "findings_detected"
    assert data["findings"][0]["category"] == "test_failure"
    assert data["findings"][0]["line_number"] == 2
    assert data["human_review_required"] is True


def test_gitlab_job_investigation_handles_unrecognized_trace(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "gitlab_job_trace",
        lambda job_id: {
            "job_id": job_id,
            "source": "GitLab job trace",
            "trace": "Preparing environment\nDownloading dependencies\n",
            "truncated": False,
            "human_review_required": True,
        },
    )

    response = client.post("/api/agents/ci-investigator/gitlab/456")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == 456
    assert data["status"] == "unknown"
    assert data["findings"] == []
    assert data["human_review_required"] is True


def test_gitlab_job_investigation_preserves_trace_errors(monkeypatch):
    from fastapi import HTTPException

    def fake_trace(job_id):
        raise HTTPException(
            status_code=404,
            detail="GitLab job was not found.",
        )

    monkeypatch.setattr(app_module, "gitlab_job_trace", fake_trace)

    response = client.post("/api/agents/ci-investigator/gitlab/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "GitLab job was not found."

def test_release_passport_blocks_detected_ci_findings():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "passport-ci-demo-001",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
            ],
            "ci_evidence": [
                {
                    "source": "gitlab_job_trace",
                    "job_id": 456,
                    "status": "findings_detected",
                    "findings": [
                        {
                            "category": "test_failure",
                            "title": "Automated test failure",
                            "line_number": 12,
                        }
                    ],
                    "verification": "not_verified",
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "blocked"
    assert result["release_approved"] is False
    assert result["human_action_required"] is True
    assert result["findings"][0]["source"] == "gitlab_job_trace"
    assert result["findings"][0]["job_id"] == 456
    assert result["findings"][0]["verification"] == "not_verified"


def test_release_passport_keeps_unknown_ci_result_pending():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "passport-ci-demo-002",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
            ],
            "ci_evidence": [
                {
                    "source": "gitlab_job_trace",
                    "job_id": 789,
                    "status": "unknown",
                    "findings": [],
                    "verification": "not_verified",
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "pending"
    assert result["release_approved"] is False
    assert result["human_action_required"] is True
    assert result["findings"][0]["job_id"] == 789
    assert result["findings"][0]["status"] == "unknown"


def test_release_passport_explains_blocked_ci_findings():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "explain-blocked-001",
            "checks": [{"name": "pytest", "status": "passed"}],
            "ci_evidence": [
                {
                    "source": "gitlab_job_trace",
                    "job_id": 901,
                    "status": "findings_detected",
                    "findings": [{"category": "test_failure"}],
                    "verification": "not_verified",
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    explanation = result["decision_explanation"]

    assert result["decision"] == "blocked"
    assert explanation["code"] == "blocked"
    assert "blocked" in explanation["message"].lower()
    assert explanation["reasons"]
    assert explanation["next_steps"]
    assert result["release_approved"] is False


def test_release_passport_explains_incomplete_ci_evidence():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "explain-pending-001",
            "checks": [{"name": "pytest", "status": "passed"}],
            "ci_evidence": [
                {
                    "source": "gitlab_job_trace",
                    "job_id": 902,
                    "status": "findings_detected",
                    "findings": [],
                    "verification": "not_verified",
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    explanation = result["decision_explanation"]

    assert result["decision"] == "pending"
    assert explanation["code"] == "pending"
    assert any(
        "contained no findings" in reason
        for reason in explanation["reasons"]
    )
    assert explanation["next_steps"]
    assert result["release_approved"] is False


def test_release_passport_explains_human_review_requirement():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "explain-review-001",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    explanation = result["decision_explanation"]

    assert result["decision"] == "ready_for_human_review"
    assert explanation["code"] == "ready_for_human_review"
    assert "human review" in explanation["message"].lower()
    assert explanation["next_steps"]
    assert result["release_approved"] is False
    assert result["human_action_required"] is True

def test_release_passport_includes_evidence_fingerprint():
    response = client.post(
        "/api/release-passport",
        json={
            "commit": "integrity-demo-001",
            "checks": [
                {"name": "pytest", "status": "passed", "evidence": "37 tests passed"},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    integrity = result["evidence_integrity"]

    assert integrity["algorithm"] == "sha256"
    assert len(integrity["fingerprint"]) == 64
    assert integrity["scope"] == ["commit", "checks", "ci_evidence"]
    assert integrity["verification"] == "fingerprinted_not_authenticated"
    assert result["decision"] == "ready_for_human_review"
    assert result["release_approved"] is False
    assert result["human_action_required"] is True


def test_release_passport_fingerprint_is_deterministic():
    payload = {
        "commit": "integrity-demo-002",
        "checks": [
            {"name": "pytest", "status": "passed", "evidence": "All tests passed"},
        ],
    }

    first = client.post("/api/release-passport", json=payload)
    second = client.post("/api/release-passport", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        first.json()["evidence_integrity"]["fingerprint"]
        == second.json()["evidence_integrity"]["fingerprint"]
    )


def test_release_passport_fingerprint_changes_when_evidence_changes():
    base = {
        "commit": "integrity-demo-003",
        "checks": [
            {"name": "pytest", "status": "passed", "evidence": "Original evidence"},
        ],
    }
    changed = {
        "commit": "integrity-demo-003",
        "checks": [
            {"name": "pytest", "status": "passed", "evidence": "Changed evidence"},
        ],
    }

    first = client.post("/api/release-passport", json=base)
    second = client.post("/api/release-passport", json=changed)

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        first.json()["evidence_integrity"]["fingerprint"]
        != second.json()["evidence_integrity"]["fingerprint"]
    )
