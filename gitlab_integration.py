import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException

router = APIRouter()

GITLAB_API = "https://gitlab.com/api/v4"
PROJECT_PATH = os.getenv(
    "GITLAB_PROJECT_PATH",
    "aftercode-team/aftercode",
)


def gitlab_get(path: str, params: dict | None = None):
    token = os.getenv("GITLAB_TOKEN")

    if not token:
        raise HTTPException(
            status_code=503,
            detail="GitLab integration is not configured.",
        )

    url = f"{GITLAB_API}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "PRIVATE-TOKEN": token,
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(
                status_code=404,
                detail="GitLab pipeline or project was not found.",
            ) from None
        if exc.code in (401, 403):
            raise HTTPException(
                status_code=502,
                detail="GitLab rejected the configured API credentials.",
            ) from None
        raise HTTPException(
            status_code=502,
            detail="GitLab API request failed.",
        ) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve valid data from GitLab.",
        ) from None


@router.get("/api/gitlab/release-passport")
def gitlab_release_passport(ref: str = "main"):
    if not ref.strip() or len(ref) > 250:
        raise HTTPException(
            status_code=400,
            detail="A valid branch or ref is required.",
        )

    project = quote(PROJECT_PATH, safe="")
    pipelines = gitlab_get(
        f"/projects/{project}/pipelines",
        {"ref": ref, "per_page": 1},
    )

    if not isinstance(pipelines, list) or not pipelines:
        raise HTTPException(
            status_code=404,
            detail="No pipeline was found for this ref.",
        )

    pipeline = pipelines[0]
    pipeline_id = pipeline.get("id")

    if pipeline_id is None:
        raise HTTPException(
            status_code=502,
            detail="GitLab returned incomplete pipeline metadata.",
        )

    jobs = gitlab_get(
        f"/projects/{project}/pipelines/{pipeline_id}/jobs",
        {"per_page": 100, "include_retried": "false"},
    )

    if not isinstance(jobs, list) or not jobs:
        raise HTTPException(
            status_code=502,
            detail="No job evidence was returned; release review cannot proceed.",
        )

    checks = []
    findings = []

    for job in jobs:
        raw_status = job.get("status", "unknown")

        if raw_status == "success":
            status = "passed"
        elif raw_status == "failed":
            status = "failed"
        else:
            status = "not_run"

        name = job.get("name") or "unnamed job"
        evidence = (
            f"GitLab job status: {raw_status}; "
            f"stage: {job.get('stage', 'unknown')}; "
            f"job ID: {job.get('id', 'unknown')}; "
            f"allow_failure: {job.get('allow_failure', False)}."
        )

        checks.append({
            "name": name,
            "status": status,
            "evidence": evidence,
            "gitlab_job_url": job.get("web_url"),
        })

        if status != "passed":
            findings.append({
                "check": name,
                "status": status,
                "evidence": evidence,
            })

    passed = sum(c["status"] == "passed" for c in checks)
    failed = sum(c["status"] == "failed" for c in checks)
    not_run = sum(c["status"] == "not_run" for c in checks)

    if failed:
        decision = "blocked"
    elif not_run:
        decision = "pending"
    else:
        decision = "ready_for_human_review"

    return {
        "product": "AfterCode",
        "artifact": "release_passport",
        "source": "GitLab API",
        "pipeline": {
            "id": pipeline_id,
            "status": pipeline.get("status"),
            "ref": pipeline.get("ref"),
            "commit": pipeline.get("sha"),
            "url": pipeline.get("web_url"),
        },
        "decision": decision,
        "release_approved": False,
        "summary": {
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
            "not_run": not_run,
        },
        "checks": checks,
        "findings": findings,
        "human_action_required": True,
        "decision_policy": (
            "Only successful jobs count as passed. Failed jobs block "
            "the recommendation. Other statuses remain unverified. "
            "A successful review recommendation never authorizes "
            "production deployment automatically."
        ),
    }
