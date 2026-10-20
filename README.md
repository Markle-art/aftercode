# AfterCode

Agentic automation for the post-code DevSecOps lifecycle using GitLab Duo Agent Platform.

## Problem

Developers spend time coordinating code reviews, testing, security scanning, release decisions, and deployment verification. These tasks can be slow, fragmented, and difficult to audit.

## Solution

AfterCode is a new project that demonstrates how AI agents and workflows can automate the software lifecycle after code is written, while keeping release decisions under appropriate human control.

## Current Capabilities

- FastAPI health and release-readiness endpoints
- Automated unit tests with pytest
- Code quality checks with Ruff
- Dependency vulnerability auditing with pip-audit
- Static security analysis with Semgrep
- CI/CD packaging and build artifacts
- GitLab pipeline-based governance checks
- Project-specific instructions for AI agents

## Technology Stack

- Python 3.12+
- FastAPI
- pytest
- Ruff
- pip-audit
- Semgrep
- GitLab CI/CD
- GitLab Duo Agent Platform

## Prerequisites

- Python 3.12 or newer
- Git
- A GitLab account
- Access to GitLab Duo Agent Platform for agentic features

## Run Locally

Open PowerShell in the repository directory.

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run the lint checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check app.py test_app.py
```

Start the application:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open these endpoints in your browser:

- Application: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- API documentation: http://127.0.0.1:8000/docs
- Release readiness: http://127.0.0.1:8000/release-readiness

Stop the development server by pressing Ctrl+C in PowerShell.

## Release Passport Demonstration

Run the reproducible API demonstration from the repository root:

``powershell
python .\demo_release_passport.py
``

The demonstration exercises three scenarios:

1. **Blocked:** a failed check prevents release readiness.
2. **Pending:** unknown CI evidence requires further verification.
3. **Ready for human review:** checks pass, but human approval is still required.

Each scenario prints its decision explanation and approval flags. The script asserts that no scenario automatically approves a release.

The demonstration uses FastAPI's in-process test client. It does not deploy software or contact a live GitLab job.

## GitLab CI/CD

The `.gitlab-ci.yml` pipeline is configured to run:

1. Unit tests
2. Code linting
3. Dependency vulnerability auditing
4. Static security analysis
5. Package building
6. Governance checks

Pipeline execution and results can be inspected in the GitLab project's Build > Pipelines section.

Some security checks require network access to download their tools and security data.

## Agentic Automation

AfterCode is designed to use GitLab Duo Agent Platform agents, flows, triggers, and supported tool integrations to coordinate review, remediation, verification, and release decisions.

Agentic features must be configured and tested in GitLab before they can be considered operational. The project does not treat a proposed fix as successful until the relevant checks have been rerun and passed.

Production deployment must remain subject to the configured approval policy.

## Project Structure

```text
aftercode/
├── app.py
├── test_app.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .gitlab-ci.yml
├── .gitignore
├── AGENTS.md
├── LICENSE
└── README.md
```

## Security

- Do not commit API keys, passwords, access tokens, or other secrets.
- Use GitLab CI/CD variables for sensitive configuration.
- Investigate security findings rather than disabling checks to obtain a passing pipeline.
- Require verification before treating a remediation as complete.
- Protect production deployment with an appropriate approval gate.

## Project Status

This project is being developed for the Life After Code GitLab Transcend Hackathon. Features documented as planned are not considered complete until implemented and verified.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
