import json

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

scenarios = [
    {
        "name": "BLOCKED RELEASE",
        "payload": {
            "commit": "demo-blocked-001",
            "checks": [
                {
                    "name": "pytest",
                    "status": "failed",
                    "evidence": "A regression test failed.",
                },
                {
                    "name": "semgrep",
                    "status": "passed",
                },
            ],
        },
    },
    {
        "name": "PENDING RELEASE",
        "payload": {
            "commit": "demo-pending-001",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
            ],
            "ci_evidence": [
                {
                    "source": "gitlab_job_trace",
                    "job_id": 902,
                    "status": "unknown",
                    "findings": [],
                    "verification": "not_verified",
                }
            ],
        },
    },
    {
        "name": "READY FOR HUMAN REVIEW",
        "payload": {
            "commit": "demo-review-001",
            "checks": [
                {"name": "pytest", "status": "passed"},
                {"name": "semgrep", "status": "passed"},
            ],
        },
    },
]


def main():
    for scenario in scenarios:
        response = client.post(
            "/api/release-passport",
            json=scenario["payload"],
        )

        print("\n" + "=" * 60)
        print(scenario["name"])
        print("=" * 60)
        print("HTTP status:", response.status_code)

        if response.status_code != 200:
            print(response.text)
            raise SystemExit("Demo failed; inspect the response above.")

        result = response.json()
        print(
            json.dumps(
                {
                    "commit": result["commit"],
                    "decision": result["decision"],
                    "decision_explanation": result["decision_explanation"],
                    "release_approved": result["release_approved"],
                    "human_action_required": result["human_action_required"],
                },
                indent=2,
            )
        )

        assert result["release_approved"] is False
        assert result["human_action_required"] is True

    print("\nAll three demo scenarios completed successfully.")


if __name__ == "__main__":
    main()
