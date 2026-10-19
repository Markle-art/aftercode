import re


def investigate_ci_log(log: str) -> dict:
    """Identify recognizable CI failures using evidence from the supplied log."""
    if not log.strip():
        return {
            "status": "unknown",
            "findings": [],
            "message": "The log is empty; no diagnosis can be supported.",
            "human_review_required": True,
        }

    lines = log.splitlines()
    findings = []

    patterns = [
        (
            "test_failure",
            re.compile(
                r"FAILED\s+\S+|"
                r"AssertionError|"
                r"pytest.*\bfailed\b|"
                r"\b\d+\s+failed\b",
                re.IGNORECASE,
            ),
            "Automated test failure",
            "Inspect the failing test and its assertion, then rerun that test.",
        ),
        (
            "ruff_violation",
            re.compile(
                r":\s*[A-Z]\d{3}\b|"
                r"Found\s+\d+\s+errors?",
                re.IGNORECASE,
            ),
            "Possible Ruff lint violation",
            "Inspect the reported rule code and file location, then rerun Ruff.",
        ),
        (
            "dependency_audit",
            re.compile(
                r"Found\s+\d+\s+known vulnerabilities?|"
                r"Vulnerability found|"
                r"pip-audit.*(?:failed|error)",
                re.IGNORECASE,
            ),
            "Possible dependency vulnerability",
            "Review the affected package and advisory before selecting a remediation.",
        ),
        (
            "semgrep_finding",
            re.compile(
                r"Findings:\s*[1-9]\d*|"
                r"rule_id:|"
                r"semgrep.*\bfindings?\b",
                re.IGNORECASE,
            ),
            "Possible static-analysis finding",
            "Review the finding, rule, and source location before changing code.",
        ),
    ]

    for line_number, line in enumerate(lines, start=1):
        for category, pattern, title, recommendation in patterns:
            if pattern.search(line):
                findings.append(
                    {
                        "category": category,
                        "title": title,
                        "evidence": line.strip()[:500],
                        "line_number": line_number,
                        "recommendation": recommendation,
                        "verification": "not_verified",
                    }
                )
                break

    if findings:
        status = "findings_detected"
        message = (
            "Recognizable failure patterns were found. "
            "Review the evidence; diagnoses are not proof of root cause."
        )
    else:
        status = "unknown"
        message = (
            "No supported failure pattern was recognized. "
            "The log does not establish that the job passed."
        )

    return {
        "status": status,
        "findings": findings,
        "message": message,
        "human_review_required": True,
    }
