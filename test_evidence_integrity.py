import pytest

from evidence_integrity import (
    evidence_fingerprint,
    verify_evidence_fingerprint,
)


def test_fingerprint_is_deterministic():
    evidence = {"commit": "abc123", "status": "passed"}

    assert evidence_fingerprint(evidence) == evidence_fingerprint(evidence)


def test_fingerprint_ignores_dictionary_key_order():
    first = {"commit": "abc123", "checks": {"pytest": "passed", "ruff": "passed"}}
    second = {"checks": {"ruff": "passed", "pytest": "passed"}, "commit": "abc123"}

    assert evidence_fingerprint(first) == evidence_fingerprint(second)


def test_valid_fingerprint_verifies():
    evidence = {"commit": "abc123", "status": "passed"}
    fingerprint = evidence_fingerprint(evidence)

    assert verify_evidence_fingerprint(evidence, fingerprint)


def test_modified_evidence_fails_verification():
    original = {"commit": "abc123", "status": "passed"}
    fingerprint = evidence_fingerprint(original)
    modified = {"commit": "abc123", "status": "failed"}

    assert not verify_evidence_fingerprint(modified, fingerprint)


@pytest.mark.parametrize("fingerprint", ["", "invalid", "a" * 63, "g" * 64])
def test_invalid_fingerprint_is_rejected(fingerprint):
    assert not verify_evidence_fingerprint({"status": "passed"}, fingerprint)


def test_fingerprint_rejects_nan():
    with pytest.raises(ValueError):
        evidence_fingerprint({"measurement": float("nan")})
