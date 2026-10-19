from ci_investigator import investigate_ci_log


def test_detects_pytest_failure_with_line_evidence():
    log = (
        "============================= test session starts =============================\n"
        "FAILED test_app.py::test_health - AssertionError: expected 200, got 500\n"
    )

    result = investigate_ci_log(log)

    assert result["status"] == "findings_detected"
    assert result["findings"][0]["category"] == "test_failure"
    assert result["findings"][0]["line_number"] == 2
    assert "AssertionError" in result["findings"][0]["evidence"]
    assert result["findings"][0]["verification"] == "not_verified"


def test_detects_ruff_rule_code():
    log = "app.py:12:5: F401 [*] unused import\n"

    result = investigate_ci_log(log)

    assert result["status"] == "findings_detected"
    assert result["findings"][0]["category"] == "ruff_violation"
    assert result["findings"][0]["line_number"] == 1


def test_detects_dependency_audit_vulnerability():
    log = "Found 2 known vulnerabilities in 1 package\n"

    result = investigate_ci_log(log)

    assert result["status"] == "findings_detected"
    assert result["findings"][0]["category"] == "dependency_audit"


def test_detects_semgrep_finding():
    log = "Findings: 1 (1 blocking)\n"

    result = investigate_ci_log(log)

    assert result["status"] == "findings_detected"
    assert result["findings"][0]["category"] == "semgrep_finding"


def test_unknown_log_does_not_invent_a_diagnosis():
    log = "Preparing environment\nDownloading dependencies\n"

    result = investigate_ci_log(log)

    assert result["status"] == "unknown"
    assert result["findings"] == []
    assert result["human_review_required"] is True


def test_empty_log_is_unknown():
    result = investigate_ci_log("")

    assert result["status"] == "unknown"
    assert result["findings"] == []
