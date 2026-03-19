from fastapi.testclient import TestClient

from app.main import app
from app.services import RISKY_CONFIDENCE, VERIFIED_CONFIDENCE

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_discover_returns_ten_ranked_results() -> None:
    response = client.post(
        "/v1/discover",
        json={"first_name": "John", "last_name": "Smith", "domain": "acme.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 10
    assert body["results"][0]["email"] == "john.smith@acme.com"
    assert body["results"][0]["confidence"] >= body["results"][-1]["confidence"]


def test_verify_invalid_email_keyword() -> None:
    response = client.post("/v1/verify", json={"email": "invalid.user@acme.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "invalid"


def test_verify_risky_short_local_part() -> None:
    response = client.post("/v1/verify", json={"email": "ab@acme.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "risky"
    assert response.json()["confidence"] == RISKY_CONFIDENCE


def test_verify_verified_email() -> None:
    response = client.post("/v1/verify", json={"email": "jane.doe@acme.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "verified"
    assert response.json()["confidence"] == VERIFIED_CONFIDENCE


def test_discover_empty_after_sanitization_returns_empty_results() -> None:
    response = client.post(
        "/v1/discover",
        json={"first_name": "!!!", "last_name": "###", "domain": "acme.com"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []
