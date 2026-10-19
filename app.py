from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from gitlab_integration import router as gitlab_router

app = FastAPI(
    title="AfterCode",
    description="Evidence-driven DevSecOps investigation and release readiness",
    version="0.2.0",
)


class CheckEvidence(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    status: Literal["passed", "failed", "not_run"]
    evidence: str = Field(default="", max_length=2000)


class InvestigationRequest(BaseModel):
    commit: str = Field(min_length=1, max_length=100)
    checks: list[CheckEvidence] = Field(min_length=1, max_length=50)


@app.get("/")
def root():
    return {
        "name": "AfterCode",
        "purpose": "Automate the post-code DevSecOps lifecycle",
        "status": "running",
        "agents": ["investigator"],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/release-readiness")
def release_readiness():
    return {
        "ready": False,
        "decision": "pending",
        "reason": "Release verification has not completed.",
    }


@app.post("/api/agents/investigator")
def investigate(request: InvestigationRequest):
    findings = []

    for check in request.checks:
        if check.status == "failed":
            findings.append(
                {
                    "severity": "high",
                    "check": check.name,
                    "status": "failed",
                    "finding": (
                        check.evidence
                        or "The check failed, but no explanatory evidence was supplied."
                    ),
                }
            )
        elif check.status == "not_run":
            findings.append(
                {
                    "severity": "unknown",
                    "check": check.name,
                    "status": "not_run",
                    "finding": (
                        check.evidence
                        or "This check has not run; its result is unknown."
                    ),
                }
            )

    failed = sum(c.status == "failed" for c in request.checks)
    not_run = sum(c.status == "not_run" for c in request.checks)
    passed = sum(c.status == "passed" for c in request.checks)

    if failed:
        decision = "blocked"
    elif not_run:
        decision = "pending"
    else:
        decision = "checks_passed"

    return {
        "agent": "investigator",
        "commit": request.commit,
        "summary": {
            "passed": passed,
            "failed": failed,
            "not_run": not_run,
        },
        "findings": findings,
        "recommendation": decision,
        "release_approved": False,
        "note": (
            "This report reflects only the evidence supplied. "
            "The investigator cannot approve a production release."
        ),
    }

@app.post("/api/agents/security-analyst")
def security_analyst(request: InvestigationRequest):
    findings = []

    for check in request.checks:
        if check.status == "failed":
            findings.append(
                {
                    "check": check.name,
                    "risk": "high",
                    "status": "failed",
                    "evidence": (
                        check.evidence
                        or "Check failed; supporting details were not supplied."
                    ),
                    "action": "Investigate and resolve the failure, then rerun the check.",
                }
            )
        elif check.status == "not_run":
            findings.append(
                {
                    "check": check.name,
                    "risk": "unknown",
                    "status": "not_run",
                    "evidence": (
                        check.evidence
                        or "No result is available for this check."
                    ),
                    "action": "Run this check before making a release decision.",
                }
            )

    failed = sum(c.status == "failed" for c in request.checks)
    not_run = sum(c.status == "not_run" for c in request.checks)

    if failed:
        assessment = "risks_detected"
    elif not_run:
        assessment = "incomplete"
    else:
        assessment = "no_reported_findings"

    return {
        "agent": "security-analyst",
        "commit": request.commit,
        "assessment": assessment,
        "checks_reviewed": len(request.checks),
        "failed_checks": failed,
        "checks_not_run": not_run,
        "findings": findings,
        "release_approved": False,
        "limitation": (
            "This assessment classifies supplied check results. "
            "It does not run security scans or prove the application is secure."
        ),
    }

@app.post("/api/release-passport")
def release_passport(request: InvestigationRequest):
    check_records = []
    findings = []

    for check in request.checks:
        check_records.append(
            {
                "name": check.name,
                "status": check.status,
                "evidence": check.evidence or None,
            }
        )

        if check.status == "failed":
            findings.append(
                {
                    "check": check.name,
                    "status": "failed",
                    "evidence": (
                        check.evidence
                        or "The check failed without additional evidence."
                    ),
                }
            )
        elif check.status == "not_run":
            findings.append(
                {
                    "check": check.name,
                    "status": "not_run",
                    "evidence": (
                        check.evidence
                        or "The check has not run; its result is unknown."
                    ),
                }
            )

    passed = sum(c.status == "passed" for c in request.checks)
    failed = sum(c.status == "failed" for c in request.checks)
    not_run = sum(c.status == "not_run" for c in request.checks)

    if failed:
        decision = "blocked"
    elif not_run:
        decision = "pending"
    else:
        decision = "ready_for_human_review"

    return {
        "product": "AfterCode",
        "artifact": "release_passport",
        "commit": request.commit,
        "decision": decision,
        "release_approved": False,
        "summary": {
            "total_checks": len(request.checks),
            "passed": passed,
            "failed": failed,
            "not_run": not_run,
        },
        "checks": check_records,
        "findings": findings,
        "human_action_required": True,
        "decision_policy": (
            "A failed check blocks the recommendation. "
            "An unrun check keeps it pending. "
            "Passing submitted checks permits human review only."
        ),
    }

app.include_router(gitlab_router)
