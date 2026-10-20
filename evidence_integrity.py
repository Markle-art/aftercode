import hashlib
import json
import re
from typing import Any


def evidence_fingerprint(evidence: Any) -> str:
    """Return a deterministic SHA-256 fingerprint of JSON-compatible evidence."""
    canonical = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_evidence_fingerprint(evidence: Any, expected_fingerprint: str) -> bool:
    """Check content consistency against a previously recorded SHA-256 fingerprint."""
    if not isinstance(expected_fingerprint, str):
        return False

    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_fingerprint):
        return False

    actual_fingerprint = evidence_fingerprint(evidence)
    return actual_fingerprint == expected_fingerprint.lower()
