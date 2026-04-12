from fastapi.testclient import TestClient

from ustreamer_api.api import create_app
from ustreamer_api.models.db import Timelapse

        # total_frames = self.event_duration * self.target_fps
        # return self.timelapse_duration / total_frames

EXPECTED_EVT_DURATION = 60
EXPECTED_TIMELAPSE_DURATION = 10
EXPECTED_TARGET_FPS = 24
EXPECTED_SHOT_INTERVAL = 0.25


def test_start_timelapse_creates_record(monkeypatch, tmp_path) -> None:
    """Creating a timelapse returns the persisted record."""
    monkeypatch.setenv("USTREAMER_API_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_API_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        response = client.post(
            "/timelapses",
            json={
                "event_duration": EXPECTED_EVT_DURATION,
                "target_duration": EXPECTED_TIMELAPSE_DURATION,
                "target_fps": EXPECTED_TARGET_FPS,
            },
        )

    assert response.status_code == 201

    body = response.json()
    timelapse = Timelapse(**body)
    assert timelapse.event_duration == EXPECTED_EVT_DURATION
    assert timelapse.target_duration == EXPECTED_TIMELAPSE_DURATION
    assert timelapse.target_fps == EXPECTED_TARGET_FPS
    assert abs(timelapse.shot_interval() - EXPECTED_SHOT_INTERVAL) < 0.001
    assert timelapse.id
