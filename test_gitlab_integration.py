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


def test_gitlab_job_trace_returns_log(monkeypatch):
    def fake_urlopen(request, timeout):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return b"pytest: 15 passed"

        return FakeResponse()

    monkeypatch.setenv("GITLAB_TOKEN", "test-token")
    monkeypatch.setattr(
        gitlab_integration,
        "urlopen",
        fake_urlopen,
        raising=False,
    )

    response = client.get("/api/gitlab/jobs/456/trace")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == 456
    assert data["trace"] == "pytest: 15 passed"
    assert data["truncated"] is False
    assert data["human_review_required"] is True


def test_gitlab_job_trace_rejects_nonpositive_id():
    response = client.get("/api/gitlab/jobs/0/trace")

    assert response.status_code == 400


def test_gitlab_job_trace_requires_token(monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)

    response = client.get("/api/gitlab/jobs/456/trace")

    assert response.status_code == 503


def test_gitlab_job_trace_truncates_large_logs(monkeypatch):
    def fake_urlopen(request, timeout):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                assert limit == 2_000_001
                return b"x" * limit

        return FakeResponse()

    monkeypatch.setenv("GITLAB_TOKEN", "test-token")
    monkeypatch.setattr(
        gitlab_integration,
        "urlopen",
        fake_urlopen,
        raising=False,
    )

    response = client.get("/api/gitlab/jobs/456/trace")

    assert response.status_code == 200
    data = response.json()
    assert len(data["trace"]) == 2_000_000
    assert data["truncated"] is True


def test_gitlab_job_trace_handles_missing_job(monkeypatch):
    from urllib.error import HTTPError

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            {},
            None,
        )

    monkeypatch.setenv("GITLAB_TOKEN", "test-token")
    monkeypatch.setattr(
        gitlab_integration,
        "urlopen",
        fake_urlopen,
        raising=False,
    )

    response = client.get("/api/gitlab/jobs/999999/trace")

    assert response.status_code == 404
    assert response.json()["detail"] == "GitLab job was not found."
