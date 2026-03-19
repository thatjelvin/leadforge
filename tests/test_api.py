from fastapi.testclient import TestClient

from app.main import app

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
