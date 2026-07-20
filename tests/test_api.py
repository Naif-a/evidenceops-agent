from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_endpoint_returns_404() -> None:
    response = client.get("/unknown")

    assert response.status_code == 404
