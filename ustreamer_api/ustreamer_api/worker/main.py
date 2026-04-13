import concurrent.futures
import contextlib
import logging
import multiprocessing
import os
import random
import signal
import time
import typing
import uuid

import sqlalchemy
import sqlalchemy.orm

from ..models.db import Timelapse
from ..models.db import get_engine
from ..settings import WorkerSettings
from ..settings import get_common_settings
from ..settings import get_worker_settings
from ._capture import capture_timelapse


_LOG_ROOT = __name__.split(".")[0]
base_logger = logging.getLogger(__name__)


class _PackageOnlyFilter(logging.Filter):
    """Allow only logs rooted in the ustreamer_api package."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return whether the log record belongs to the package logger tree."""
        return record.name == _LOG_ROOT or record.name.startswith(f"{_LOG_ROOT}.")


def _configure_logging(settings: WorkerSettings) -> None:
    """Configure worker logging based on the application settings."""
    log_level = logging.getLevelNamesMapping()[settings.log_level]
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s][%(levelname)s][%(name)s]: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    if log_level > logging.DEBUG:
        package_filter = _PackageOnlyFilter()
        handler.addFilter(package_filter)
        for logger_name, logger_obj in root_logger.manager.loggerDict.items():
            if isinstance(logger_obj, logging.Logger) and not (
                logger_name == __package__ or logger_name.startswith(f"{__package__}.")
            ):
                logger_obj.disabled = True

    logging.basicConfig(level=log_level, handlers=[handler], force=True)


@contextlib.contextmanager
def _get_db_engine(db_file: str) -> typing.Iterator[sqlalchemy.Engine]:
    """Create and return a new database session."""
    engine = get_engine(db_file)
    try:
        yield engine
    finally:
        engine.dispose()

def process_job(job_id: uuid.UUID, db_file: str, settings: WorkerSettings) -> uuid.UUID:
    """Fetch a the job with the given id from the database and start generating the timelapse frames."""
    logger = base_logger.getChild("pid-%d" % os.getpid())
    logger.info(f"Processing job {job_id}...")
    with _get_db_engine(db_file) as db_engine:
        with sqlalchemy.orm.Session(db_engine) as session:
            timelapse = session.get(Timelapse, job_id)
            if timelapse is not None:
                capture_timelapse(logger, timelapse, settings)
                session.add(timelapse)
                session.commit()
            else:
                logger.warning(f"Job {job_id} not found in the database")
                return job_id

            time.sleep(random.randint(1, 3))
            logger.info(f"Finished processing job {job_id}")
    return job_id


def worker_main() -> None:
    """Worker process function to perform background tasks."""
    worker_settings = get_worker_settings()
    common_settings = get_common_settings()
    _configure_logging(worker_settings)

    stop_requested = False

    def _handle_sigint(signum: int, frame: typing.Any) -> None:
        """Request worker shutdown after the current loop iteration completes."""
        nonlocal stop_requested
        stop_requested = True
        base_logger.info("Received signal %s; waiting for jobs to complete...", signum)

    previous_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        with _get_db_engine(common_settings.db_file) as db_engine, concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            base_logger.info("Waiting for jobs...")
            base_logger.info("Press Ctrl+C to stop")
            while True:
                frame_start = time.time()
                with sqlalchemy.orm.Session(db_engine) as session:
                    active_job_ids = Timelapse.find_active_ids(session)

                if active_job_ids:
                    base_logger.info("Executing %d jobs...", len(active_job_ids))

                procs = []
                for job_id in active_job_ids:
                    proc = executor.submit(process_job, job_id, common_settings.db_file, worker_settings)
                    procs.append(proc)

                for proc in concurrent.futures.as_completed(procs):
                    proc.result()

                if active_job_ids:
                    base_logger.info("Completed %d jobs", len(active_job_ids))
                    base_logger.info("Waiting for jobs...")
                    base_logger.info("Press Ctrl+C to stop")

                if stop_requested:
                    return

                frame_duration = time.time() - frame_start
                time.sleep(max(0, 1.0 - frame_duration))
    finally:
        base_logger.info("Done.")
        signal.signal(signal.SIGINT, previous_sigint_handler)
