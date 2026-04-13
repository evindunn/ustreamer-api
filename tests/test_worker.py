import concurrent.futures
import pathlib
import uuid

import fastapi.testclient
import sqlalchemy.orm

import ustreamer_api.api
import ustreamer_api.models.db
import ustreamer_api.worker.main

JOB_COUNT = 10
EVENT_DURATION = 60
TARGET_DURATION = 10
TARGET_FPS = 24


class _StopWorker(Exception):
    """Signal the worker loop to stop after one iteration."""


class _FakeExecutor:
    """Capture submitted jobs without spawning real worker processes."""

    def __init__(self, submitted_jobs: list[tuple[object, uuid.UUID, str, object]], max_workers: int) -> None:
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
        db_file: str,
        settings: object,
    ) -> concurrent.futures.Future[uuid.UUID]:
        """Return a completed future for the submitted job id."""
        self.submitted_jobs.append((fn, job_id, db_file, settings))
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
    db_file, created_job_ids = _create_timelapses_via_api(monkeypatch, tmp_path)

    submitted_jobs: list[tuple[object, uuid.UUID, str, object]] = []
    executor_instances: list[_FakeExecutor] = []

    monkeypatch.setattr(ustreamer_api.worker.main.multiprocessing, "cpu_count", lambda: JOB_COUNT)
    monkeypatch.setattr(
        ustreamer_api.worker.main.concurrent.futures,
        "ProcessPoolExecutor",
        lambda max_workers: executor_instances.append(_FakeExecutor(submitted_jobs, max_workers)) or executor_instances[-1],
    )
    monkeypatch.setattr(
        ustreamer_api.worker.main.time,
        "sleep",
        lambda _: (_ for _ in ()).throw(_StopWorker()),
    )

    try:
        ustreamer_api.worker.main.worker_main()
    except _StopWorker:
        pass

    assert len(executor_instances) == 1
    assert executor_instances[0].max_workers == JOB_COUNT
    assert len(submitted_jobs) == JOB_COUNT
    assert {job_id for _, job_id, _, _ in submitted_jobs} == set(created_job_ids)
    assert {submitted_db_file for _, _, submitted_db_file, _ in submitted_jobs} == {str(db_file)}


def test_process_job_persists_execute_side_effects(monkeypatch, tmp_path) -> None:
    """Process job loads the row, runs capture, and commits the changes."""
    db_file, created_job_ids = _create_timelapses_via_api(monkeypatch, tmp_path, count=1)
    job_id = created_job_ids[0]
    settings = ustreamer_api.worker.main.WorkerSettings()

    monkeypatch.setattr(
        ustreamer_api.worker.main,
        "capture_timelapse",
        lambda logger, timelapse, worker_settings: setattr(timelapse, "ended_at", timelapse.started_at),
    )
    monkeypatch.setattr(ustreamer_api.worker.main.random, "randint", lambda start, end: 0)
    monkeypatch.setattr(ustreamer_api.worker.main.time, "sleep", lambda _: None)

    result = ustreamer_api.worker.main.process_job(job_id, str(db_file), settings)

    engine = ustreamer_api.models.db.get_engine(str(db_file))
    with sqlalchemy.orm.Session(engine) as session:
        job = session.get(ustreamer_api.models.db.Timelapse, job_id)

    assert result == job_id
    assert job is not None
    assert job.ended_at == job.started_at


def test_process_job_commits_capture_side_effects(monkeypatch, tmp_path) -> None:
    """Process job commits the state changes made by capture_timelapse."""
    db_file, created_job_ids = _create_timelapses_via_api(monkeypatch, tmp_path, count=1)
    job_id = created_job_ids[0]
    created_output_dirs: list[pathlib.Path] = []
    settings = ustreamer_api.worker.main.WorkerSettings()

    def _fake_capture(logger: object, timelapse: ustreamer_api.models.db.Timelapse, worker_settings: object) -> None:
        """Create representative capture side effects on disk and on the model."""
        del logger
        del worker_settings
        output_dir = timelapse.image_dir(tmp_path)
        created_output_dirs.append(output_dir)
        output_dir.mkdir()
        (output_dir / "frame-000000.jpg").write_bytes(b"frame-bytes")
        timelapse.output_file(tmp_path).write_bytes(b"video-bytes")
        timelapse.end()

    monkeypatch.setattr(
        ustreamer_api.worker.main,
        "capture_timelapse",
        _fake_capture,
    )
    monkeypatch.setattr(ustreamer_api.worker.main.random, "randint", lambda start, end: 0)
    monkeypatch.setattr(ustreamer_api.worker.main.time, "sleep", lambda _: None)

    result = ustreamer_api.worker.main.process_job(job_id, str(db_file), settings)

    engine = ustreamer_api.models.db.get_engine(str(db_file))
    with sqlalchemy.orm.Session(engine) as session:
        timelapse = session.get(ustreamer_api.models.db.Timelapse, job_id)

    assert timelapse is not None
    assert result == job_id
    assert timelapse.ended_at is not None
    assert created_output_dirs == [timelapse.image_dir(tmp_path)]
    assert created_output_dirs[0].exists()
    assert timelapse.output_file(tmp_path).exists()
