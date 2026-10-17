from fastapi import FastAPI

app = FastAPI(
    title="AfterCode",
    description="Agentic DevSecOps release readiness service",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "name": "AfterCode",
        "purpose": "Automate the post-code DevSecOps lifecycle",
        "status": "running",
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
