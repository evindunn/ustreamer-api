import concurrent.futures
import pathlib
import signal
import types
import uuid

import fastapi.testclient
import sqlalchemy.orm

import ustreamer_api.api
import ustreamer_api.models.db
import ustreamer_api.worker

JOB_COUNT = 10
EVENT_DURATION = 60
TARGET_DURATION = 10
TARGET_FPS = 24


class _StopWorker(Exception):
    """Signal the worker loop to stop after one iteration."""


class _FakeExecutor:
    """Capture submitted jobs without spawning real worker processes."""

    def __init__(self, submitted_jobs: list[tuple[object, uuid.UUID, object]], max_workers: int) -> None:
        self.submitted_jobs = submitted_jobs
        self.max_workers = max_workers

    def __enter__(self) -> "_FakeExecutor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def submit(
        self,
        fn: object,
        job_id: uuid.UUID,
        settings: object,
    ) -> concurrent.futures.Future[uuid.UUID]:
        """Return a completed future for the submitted job id."""
        self.submitted_jobs.append((fn, job_id, settings))
        future: concurrent.futures.Future[uuid.UUID] = concurrent.futures.Future()
        future.set_result(job_id)
        return future


def _create_timelapses_via_api(
    monkeypatch,
    tmp_path: pathlib.Path,
    count: int = JOB_COUNT,
) -> tuple[pathlib.Path, list[uuid.UUID]]:
    """Create timelapse records through the API and return their ids."""
    db_file = tmp_path / "worker-test.sqlite"
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_DB_FILE", str(db_file))

    created_job_ids: list[uuid.UUID] = []
    with fastapi.testclient.TestClient(ustreamer_api.api.create_app()) as client:
        for _ in range(count):
            response = client.post(
                "/timelapses",
                json={
                    "event_duration": EVENT_DURATION,
                    "target_duration": TARGET_DURATION,
                    "target_fps": TARGET_FPS,
                },
            )
            assert response.status_code == 201
            created_job_ids.append(uuid.UUID(response.json()["id"]))

    return db_file, created_job_ids


def test_worker_main_submits_ten_api_created_jobs(monkeypatch, tmp_path) -> None:
    """Worker main submits one future per active job in the database."""
    _, created_job_ids = _create_timelapses_via_api(monkeypatch, tmp_path)

    submitted_jobs: list[tuple[object, uuid.UUID, object]] = []
    executor_instances: list[_FakeExecutor] = []

    monkeypatch.setattr(ustreamer_api.worker.multiprocessing, "cpu_count", lambda: JOB_COUNT)
    monkeypatch.setattr(
        ustreamer_api.worker.concurrent.futures,
        "ProcessPoolExecutor",
        lambda max_workers: executor_instances.append(_FakeExecutor(submitted_jobs, max_workers)) or executor_instances[-1],
    )
    monkeypatch.setattr(
        ustreamer_api.worker.time,
        "sleep",
        lambda _: (_ for _ in ()).throw(_StopWorker()),
    )

    try:
        ustreamer_api.worker.worker_main()
    except _StopWorker:
        pass

    assert len(executor_instances) == 1
    assert executor_instances[0].max_workers == JOB_COUNT
    assert len(submitted_jobs) == JOB_COUNT
    assert {job_id for _, job_id, _ in submitted_jobs} == set(created_job_ids)


def test_process_job_persists_execute_side_effects(monkeypatch, tmp_path) -> None:
    """Process job loads the row, runs execute, and commits the changes."""
    db_file, created_job_ids = _create_timelapses_via_api(monkeypatch, tmp_path, count=1)
    job_id = created_job_ids[0]
    settings = ustreamer_api.worker.WorkerSettings()

    monkeypatch.setattr(
        ustreamer_api.models.db.Timelapse,
        "execute",
        lambda self: setattr(self, "ended_at", self.started_at),
    )
    monkeypatch.setattr(ustreamer_api.worker.random, "randint", lambda start, end: 0)
    monkeypatch.setattr(ustreamer_api.worker.time, "sleep", lambda _: None)

    result = ustreamer_api.worker.process_job(job_id, settings)

    engine = ustreamer_api.models.db.get_engine(str(db_file))
    with sqlalchemy.orm.Session(engine) as session:
        job = session.get(ustreamer_api.models.db.Timelapse, job_id)

    assert result == job_id
    assert job is not None
    assert job.ended_at == job.started_at


def test_timelapse_execute_captures_frames_and_stops_on_sigint(monkeypatch, tmp_path) -> None:
    """Execute saves captured frames and exits cleanly when interrupted."""
    captured_handlers: dict[int, object] = {}
    fake_now = {"value": 0.0}
    request_count = {"value": 0}

    class _FakeResponse:
        """Provide a minimal successful HTTP response."""

        content = b"frame-bytes"

        def raise_for_status(self) -> None:
            """Validate the fake response."""
            return None

    class _FakeClient:
        """Capture outbound requests without making network calls."""

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str, params: dict[str, str]) -> _FakeResponse:
            """Return a successful fake snapshot response."""
            assert url == "http://camera.local"
            assert params == {"action": "snapshot"}
            request_count["value"] += 1
            return _FakeResponse()

    def _fake_sleep(duration: float) -> None:
        """Advance fake time and request shutdown after the second capture."""
        fake_now["value"] += duration
        if request_count["value"] >= 2:
            handler = captured_handlers[signal.SIGINT]
            handler(signal.SIGINT, None)

    monkeypatch.setattr(
        ustreamer_api.models.db.settings,
        "get_common_settings",
        lambda: types.SimpleNamespace(
            data_dir=tmp_path,
            db_file=":memory:",
        ),
    )
    monkeypatch.setattr(
        ustreamer_api.models.db.settings,
        "get_worker_settings",
        lambda: types.SimpleNamespace(
            ustreamer_url="http://camera.local",
        ),
    )
    monkeypatch.setattr(ustreamer_api.models.db.httpx, "Client", lambda timeout: _FakeClient())
    monkeypatch.setattr(ustreamer_api.models.db.time, "monotonic", lambda: fake_now["value"])
    monkeypatch.setattr(ustreamer_api.models.db.time, "sleep", _fake_sleep)
    monkeypatch.setattr(ustreamer_api.models.db.signal, "getsignal", lambda signum: None)
    monkeypatch.setattr(
        ustreamer_api.models.db.signal,
        "signal",
        lambda signum, handler: captured_handlers.__setitem__(signum, handler),
    )

    timelapse = ustreamer_api.models.db.Timelapse(
        event_duration=EVENT_DURATION,
        target_duration=TARGET_DURATION,
        target_fps=TARGET_FPS,
    )

    timelapse.execute()

    output_dir = tmp_path / f"{timelapse.started_at.strftime('%Y-%m-%dT%H-%M-%S')}_{timelapse.id.hex}"
    frame_paths = sorted(output_dir.glob("frame-*.jpg"))

    assert request_count["value"] == 2
    assert [path.name for path in frame_paths] == ["frame-000000.jpg", "frame-000001.jpg"]
    assert all(path.read_bytes() == b"frame-bytes" for path in frame_paths)
    assert timelapse.ended_at is not None
