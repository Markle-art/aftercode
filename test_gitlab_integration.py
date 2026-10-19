from fastapi.testclient import TestClient

import gitlab_integration
from app import app

client = TestClient(app)


def configure_gitlab(monkeypatch, jobs, pipelines=None):
    if pipelines is None:
        pipelines = [{
            "id": 123,
            "status": "success",
            "ref": "main",
            "sha": "abc123",
            "web_url": "https://gitlab.com/example/pipeline/123",
        }]

    def fake_gitlab_get(path, params=None):
        if path.endswith("/pipelines"):
            return pipelines
        if "/jobs" in path:
            return jobs
        raise AssertionError(f"Unexpected GitLab API path: {path}")

    monkeypatch.setattr(gitlab_integration, "gitlab_get", fake_gitlab_get)


def job(name, status):
    return {
        "id": 456,
        "name": name,
        "stage": "test",
        "status": status,
        "allow_failure": False,
        "web_url": "https://gitlab.com/example/job/456",
    }


def test_live_passport_maps_successful_jobs_to_human_review(monkeypatch):
    configure_gitlab(
        monkeypatch,
        [job("test", "success"), job("semgrep", "success")],
    )

    response = client.get("/api/gitlab/release-passport?ref=main")

    assert response.status_code == 200
    passport = response.json()
    assert passport["decision"] == "ready_for_human_review"
    assert passport["summary"]["passed"] == 2
    assert passport["summary"]["failed"] == 0
    assert passport["release_approved"] is False
    assert passport["human_action_required"] is True


def test_failed_job_blocks_passport(monkeypatch):
    configure_gitlab(
        monkeypatch,
        [job("test", "success"), job("semgrep", "failed")],
    )

    response = client.get("/api/gitlab/release-passport")

    assert response.status_code == 200
    passport = response.json()
    assert passport["decision"] == "blocked"
    assert passport["summary"]["failed"] == 1
    assert passport["release_approved"] is False


def test_running_job_keeps_passport_pending(monkeypatch):
    configure_gitlab(
        monkeypatch,
        [job("test", "success"), job("package", "running")],
    )

    response = client.get("/api/gitlab/release-passport")

    assert response.status_code == 200
    passport = response.json()
    assert passport["decision"] == "pending"
    assert passport["summary"]["not_run"] == 1
    assert passport["release_approved"] is False


def test_missing_pipeline_returns_404(monkeypatch):
    configure_gitlab(monkeypatch, [], pipelines=[])

    response = client.get("/api/gitlab/release-passport")

    assert response.status_code == 404


def test_missing_jobs_does_not_approve_release(monkeypatch):
    configure_gitlab(monkeypatch, [])

    response = client.get("/api/gitlab/release-passport")

    assert response.status_code == 502
