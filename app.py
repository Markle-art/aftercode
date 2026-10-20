from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ci_investigator import investigate_ci_log
from evidence_integrity import evidence_fingerprint
from gitlab_integration import gitlab_job_trace
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



class CILogRequest(BaseModel):
    log: str = Field(max_length=2_000_000)

class CIEvidence(BaseModel):
    source: Literal["gitlab_job_trace"]
    job_id: int = Field(ge=1)
    status: Literal["findings_detected", "unknown"]
    findings: list[dict] = Field(max_length=100)
    verification: Literal["not_verified"] = "not_verified"


class InvestigationRequest(BaseModel):
    commit: str = Field(min_length=1, max_length=100)
    checks: list[CheckEvidence] = Field(min_length=1, max_length=50)
    ci_evidence: list[CIEvidence] = Field(default_factory=list, max_length=20)


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

    ci_findings_detected = any(
        item.status == "findings_detected" and bool(item.findings)
        for item in request.ci_evidence
    )
    ci_unknown = any(
        item.status == "unknown"
        for item in request.ci_evidence
    )
    ci_incomplete = any(
        item.status == "findings_detected" and not item.findings
        for item in request.ci_evidence
    )

    for item in request.ci_evidence:
        if item.status == "findings_detected":
            for ci_finding in item.findings:
                findings.append(
                    {
                        "source": item.source,
                        "job_id": item.job_id,
                        "status": "findings_detected",
                        "verification": item.verification,
                        "evidence": ci_finding,
                        "message": (
                            "A CI log indicator was detected. "
                            "A human must validate it before acting."
                        ),
                    }
                )
        else:
            findings.append(
                {
                    "source": item.source,
                    "job_id": item.job_id,
                    "status": "unknown",
                    "verification": item.verification,
                    "evidence": (
                        "The CI trace did not establish a verified result."
                    ),
                }
            )

    if failed or ci_findings_detected:
        decision = "blocked"
    elif not_run or ci_unknown or ci_incomplete:
        decision = "pending"
    else:
        decision = "ready_for_human_review"

    reasons = []
    if failed:
        reasons.append(
            f"{failed} check(s) failed and require investigation."
        )
    if ci_findings_detected:
        reasons.append(
            "CI log indicators were detected and require human validation."
        )
    if not_run:
        reasons.append(
            f"{not_run} check(s) have not run, so their results are unknown."
        )
    if ci_unknown:
        reasons.append("At least one CI result is unknown.")
    if ci_incomplete:
        reasons.append(
            "CI evidence reported findings_detected but contained no findings."
        )

    if decision == "blocked":
        explanation_message = (
            "Release readiness is blocked because failed checks or CI "
            "indicators require investigation."
        )
        next_steps = [
            "Review the failed checks and CI evidence.",
            "Validate detected indicators and address confirmed issues.",
            "Rerun relevant checks before requesting human review.",
        ]
    elif decision == "pending":
        explanation_message = (
            "Release readiness is pending because some verification "
            "results are missing, unknown, or incomplete."
        )
        next_steps = [
            "Run checks that have not completed.",
            "Retrieve or clarify unknown or incomplete CI evidence.",
            "Reassess the passport after evidence is available.",
        ]
    else:
        explanation_message = (
            "Submitted checks passed. This passport is ready for human "
            "review; the release has not been approved."
        )
        next_steps = [
            "Have an authorized human review the evidence.",
            "Record the release decision through the appropriate approval process.",
        ]

    decision_explanation = {
        "code": decision,
        "message": explanation_message,
        "reasons": reasons,
        "next_steps": next_steps,
    }

    evidence_snapshot = {
        "commit": request.commit,
        "checks": check_records,
        "ci_evidence": [
            item.model_dump(mode="json")
            for item in request.ci_evidence
        ],
    }
    integrity = {
        "algorithm": "sha256",
        "fingerprint": evidence_fingerprint(evidence_snapshot),
        "scope": ["commit", "checks", "ci_evidence"],
        "verification": "fingerprinted_not_authenticated",
        "meaning": (
            "The fingerprint identifies this evidence snapshot. "
            "It does not prove the evidence is authentic or truthful."
        ),
    }
    return {
        "product": "AfterCode",
        "artifact": "release_passport",
        "commit": request.commit,
        "evidence_integrity": integrity,
        "decision": decision,
        "decision_explanation": decision_explanation,
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
            "A failed check or detected CI log indicator blocks the recommendation. "
            "An unrun check or unknown CI result keeps it pending. "
            "CI indicators are unverified and require human validation. "
            "Passing submitted checks permits human review only; "
            "this endpoint never approves a release automatically."
        ),
    }



@app.post("/api/agents/ci-investigator")
def ci_log_investigator(request: CILogRequest):
    result = investigate_ci_log(request.log)
    return {
        "agent": "ci-investigator",
        **result,
    }


@app.post("/api/agents/ci-investigator/gitlab/{job_id}")
def investigate_gitlab_job(job_id: int):
    trace_result = gitlab_job_trace(job_id)
    investigation = investigate_ci_log(trace_result["trace"])

    return {
        "agent": "ci-investigator",
        "source": trace_result["source"],
        "job_id": trace_result["job_id"],
        "trace_truncated": trace_result["truncated"],
        **investigation,
        "human_review_required": True,
    }


app.include_router(gitlab_router)
