from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

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
