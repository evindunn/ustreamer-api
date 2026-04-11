from fastapi.testclient import TestClient

from ustreamer_api import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200

    resp_json = response.json()
    assert isinstance(resp_json, dict)
    assert resp_json.get("status", "") == "ok"
