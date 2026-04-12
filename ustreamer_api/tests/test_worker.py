import uuid
import concurrent.futures

from fastapi.testclient import TestClient
import sqlalchemy.orm

from ustreamer_api import worker
from ustreamer_api.api import create_app
from ustreamer_api.models.db import Timelapse, get_engine

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

    def submit(self, fn: object, job_id: uuid.UUID, settings: object) -> concurrent.futures.Future[uuid.UUID]:
        """Record the submitted process call for later assertions."""
        self.submitted_jobs.append((fn, job_id, settings))
        future: concurrent.futures.Future[uuid.UUID] = concurrent.futures.Future()
        future.set_result(job_id)
        return future


def _populate_timelapses(monkeypatch, tmp_path) -> tuple[object, list[uuid.UUID]]:
    """Create test timelapses through the API and return the database path and ids."""
    db_file = tmp_path / "worker-test.sqlite"
    monkeypatch.setenv("USTREAMER_API_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_API_DB_FILE", str(db_file))

    created_job_ids: list[uuid.UUID] = []
    with TestClient(create_app()) as client:
        for _ in range(JOB_COUNT):
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
    """Worker main creates one process submission per active API-created job."""
    _, created_job_ids = _populate_timelapses(monkeypatch, tmp_path)

    submitted_jobs: list[tuple[object, uuid.UUID, object]] = []
    executor_instances: list[_FakeExecutor] = []
    expected_processes = JOB_COUNT

    monkeypatch.setattr(worker.multiprocessing, "cpu_count", lambda: expected_processes)
    monkeypatch.setattr(
        worker.concurrent.futures,
        "ProcessPoolExecutor",
        lambda max_workers: executor_instances.append(_FakeExecutor(submitted_jobs, max_workers)) or executor_instances[-1],
    )
    monkeypatch.setattr(
        worker.time,
        "sleep",
        lambda _: (_ for _ in ()).throw(_StopWorker()),
    )

    try:
        worker.worker_main()
    except _StopWorker:
        pass

    assert len(executor_instances) == 1
    assert executor_instances[0].max_workers == expected_processes
    assert len(submitted_jobs) == JOB_COUNT
    assert {job_id for _, job_id, _ in submitted_jobs} == set(created_job_ids)


def test_worker_main_sets_ended_at_for_each_processed_job(monkeypatch, tmp_path) -> None:
    """Worker main marks each processed job as ended."""
    db_file, created_job_ids = _populate_timelapses(monkeypatch, tmp_path)

    monkeypatch.setattr(worker.multiprocessing, "cpu_count", lambda: JOB_COUNT)
    monkeypatch.setattr(
        worker.concurrent.futures,
        "ProcessPoolExecutor",
        lambda max_workers: _FakeExecutor([], max_workers),
    )
    monkeypatch.setattr(
        worker.time,
        "sleep",
        lambda _: (_ for _ in ()).throw(_StopWorker()),
    )

    try:
        worker.worker_main()
    except _StopWorker:
        pass

    engine = get_engine(str(db_file))
    with sqlalchemy.orm.Session(engine) as session:
        jobs = [session.get(Timelapse, job_id) for job_id in created_job_ids]

    assert all(job is not None for job in jobs)
    assert all(job.ended_at is not None for job in jobs if job is not None)
