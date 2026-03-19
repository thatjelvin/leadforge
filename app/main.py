from fastapi import FastAPI

from app.models import (
    DiscoverRequest,
    DiscoverResponse,
    EmailCandidate,
    VerifyRequest,
    VerifyResponse,
)
from app.services import generate_candidates, verify_email

app = FastAPI(title="LeadForge API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/discover", response_model=DiscoverResponse)
async def discover(payload: DiscoverRequest) -> DiscoverResponse:
    candidates = generate_candidates(payload.first_name, payload.last_name, payload.domain)
    return DiscoverResponse(
        results=[
            EmailCandidate(
                email=c.email,
                pattern=c.pattern,
                confidence=c.confidence,
                status=c.status,
            )
            for c in candidates
        ]
    )


@app.post("/v1/verify", response_model=VerifyResponse)
async def verify(payload: VerifyRequest) -> VerifyResponse:
    status, confidence = verify_email(payload.email)
    return VerifyResponse(email=payload.email, status=status, confidence=confidence)
