"""Basic API health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_expected_shape() -> None:
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "device" in data
    assert "models" in data
    assert data["models"]["cloth_generator"] in {"available", "missing"}
    assert data["models"]["tryon_model"] in {"available", "missing"}
