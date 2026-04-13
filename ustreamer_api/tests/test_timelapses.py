import datetime
from fastapi.testclient import TestClient

from ustreamer_api.api import create_app
from ustreamer_api.models.db import Timelapse
import uuid
import zoneinfo

        # total_frames = self.event_duration * self.target_fps
        # return self.timelapse_duration / total_frames

EXPECTED_EVT_DURATION = 60
EXPECTED_TIMELAPSE_DURATION = 10
EXPECTED_TARGET_FPS = 24
EXPECTED_SHOT_INTERVAL = 0.25


def test_start_timelapse_creates_record(monkeypatch, tmp_path) -> None:
    """Creating a timelapse returns the persisted record."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

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
    timelapse = Timelapse.model_validate(body)
    assert timelapse.event_duration == EXPECTED_EVT_DURATION
    assert timelapse.target_duration == EXPECTED_TIMELAPSE_DURATION
    assert timelapse.target_fps == EXPECTED_TARGET_FPS
    assert abs(timelapse.shot_interval - EXPECTED_SHOT_INTERVAL) < 0.001
    assert timelapse.id

def test_list_timelapses_returns_started_at_order_with_pagination(monkeypatch, tmp_path) -> None:
    """Listing timelapses returns start-time-ordered paginated results."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        created_ids: list[str] = []
        for _ in range(3):
            response = client.post(
                "/timelapses",
                json={
                    "event_duration": EXPECTED_EVT_DURATION,
                    "target_duration": EXPECTED_TIMELAPSE_DURATION,
                    "target_fps": EXPECTED_TARGET_FPS,
                },
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        response = client.get("/timelapses")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == created_ids

        response = client.get("/timelapses?limit=2&offset=1")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == created_ids[1:]


def test_get_timelapse_returns_created_record(monkeypatch, tmp_path) -> None:
    """Fetching a timelapse by id returns the persisted record."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/timelapses",
            json={
                "event_duration": EXPECTED_EVT_DURATION,
                "target_duration": EXPECTED_TIMELAPSE_DURATION,
                "target_fps": EXPECTED_TARGET_FPS,
            },
        )
        assert create_response.status_code == 201

        timelapse_id = create_response.json()["id"]
        response = client.get(f"/timelapses/{timelapse_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == timelapse_id
    assert body["event_duration"] == EXPECTED_EVT_DURATION
    assert body["target_duration"] == EXPECTED_TIMELAPSE_DURATION
    assert body["target_fps"] == EXPECTED_TARGET_FPS


def test_get_timelapse_returns_404_for_unknown_id(monkeypatch, tmp_path) -> None:
    """Fetching an unknown timelapse id returns a not-found response."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        response = client.get(f"/timelapses/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Timelapse not found"}


def test_delete_timelapse_removes_record_and_worker_artifacts(monkeypatch, tmp_path) -> None:
    """Deleting a timelapse removes the database row and generated files."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/timelapses",
            json={
                "event_duration": EXPECTED_EVT_DURATION,
                "target_duration": EXPECTED_TIMELAPSE_DURATION,
                "target_fps": EXPECTED_TARGET_FPS,
            },
        )
        assert create_response.status_code == 201

        timelapse = Timelapse.model_validate(create_response.json())
        image_dir = timelapse.image_dir(tmp_path)
        output_file = timelapse.output_file(tmp_path)
        image_dir.mkdir()
        (image_dir / "frame-000000.jpg").write_bytes(b"frame-bytes")
        output_file.write_bytes(b"video-bytes")

        delete_response = client.delete(f"/timelapses/{timelapse.id}")
        fetch_response = client.get(f"/timelapses/{timelapse.id}")

    assert delete_response.status_code == 204
    assert not image_dir.exists()
    assert not output_file.exists()
    assert fetch_response.status_code == 404


def test_delete_timelapse_returns_404_for_unknown_id(monkeypatch, tmp_path) -> None:
    """Deleting an unknown timelapse id returns a not-found response."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", ":memory:")

    with TestClient(create_app()) as client:
        response = client.delete(f"/timelapses/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Timelapse not found"}
