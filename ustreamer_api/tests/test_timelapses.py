from fastapi.testclient import TestClient

from ustreamer_api import create_app
from ustreamer_api.models.db import get_engine
from ustreamer_api.settings import get_settings


def test_start_timelapse_creates_record(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("USTREAMER_API_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_API_DB_FILE", ":memory:")
    get_settings.cache_clear()
    get_engine.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/timelapses",
            json={
                "event_duration": 60,
                "timelapse_duration": 10,
                "target_fps": 24,
            },
        )

    assert response.status_code == 201

    body = response.json()
    assert body["event_duration"] == 60
    assert body["timelapse_duration"] == 10
    assert body["target_fps"] == 24
    assert body["id"]
