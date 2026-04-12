import uuid
import concurrent.futures

from fastapi.testclient import TestClient

from ustreamer_api import create_app, worker


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


def test_worker_main_submits_ten_api_created_jobs(monkeypatch, tmp_path) -> None:
    """Worker main creates one process submission per active API-created job."""
    db_file = tmp_path / "worker-test.sqlite"
    monkeypatch.setenv("USTREAMER_API_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("USTREAMER_API_DB_FILE", str(db_file))

    created_job_ids: list[uuid.UUID] = []
    with TestClient(create_app()) as client:
        for _ in range(10):
            response = client.post(
                "/timelapses",
                json={
                    "event_duration": 60,
                    "target_duration": 10,
                    "target_fps": 24,
                },
            )

            assert response.status_code == 201
            created_job_ids.append(uuid.UUID(response.json()["id"]))

    submitted_jobs: list[tuple[object, uuid.UUID, object]] = []
    executor_instances: list[_FakeExecutor] = []
    expected_processes = 10

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
    assert len(submitted_jobs) == 10
    assert {job_id for _, job_id, _ in submitted_jobs} == set(created_job_ids)
