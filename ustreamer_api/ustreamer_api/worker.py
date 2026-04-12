import concurrent.futures
import contextlib
import logging
import multiprocessing
import random
import signal
import time
import uuid

import sqlalchemy
import sqlalchemy.orm

from .settings import Settings
from .models.db import get_engine, Timelapse


base_logger = logging.getLogger(__package__)


@contextlib.contextmanager
def _get_db_engine(settings: Settings) -> sqlalchemy.Engine:
    """Create and return a new database session."""
    engine = get_engine(settings.db_file)
    try:
        yield engine
    finally:
        engine.dispose()


def process_job(job_id: uuid.UUID, settings: Settings) -> uuid.UUID:
    """Fetch a the job with the given id from the database and start generating the timelapse frames."""
    logger = base_logger.getChild("pid-%d" % multiprocessing.current_process().pid)
    logger.info(f"Processing job {job_id}...")
    with _get_db_engine(settings) as db_engine:
        with sqlalchemy.orm.Session(db_engine) as session:
            timelapse = session.get(Timelapse, job_id)
            if timelapse is not None:
                logger.info(f"Processing job {job_id}...")
                timelapse.execute()
                session.add(timelapse)
                session.commit()
            else:
                logger.warning(f"Job {job_id} not found in the database")
                return job_id

            time.sleep(random.randint(1, 3))  # Simulate the time taken to process the job
            logger.info(f"Finished processing job {job_id}")
    return job_id


def worker_main():
    logging.basicConfig(
        level=logging.INFO, 
        format="[%(asctime)s][%(levelname)s][%(name)s]: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )

    """Worker process function to perform background tasks."""
    settings = Settings()
    stop_requested = False

    def _handle_sigint(signum: int, frame) -> None:
        """Request worker shutdown after the current loop iteration completes."""
        nonlocal stop_requested
        stop_requested = True
        base_logger.info("Received signal %s; waiting for jobs to complete...", signum)

    previous_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        with _get_db_engine(settings) as db_engine, concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            base_logger.info("Waiting for jobs...")
            base_logger.info("Press Ctrl+C to stop")
            while True:
                frame_start = time.time()
                with sqlalchemy.orm.Session(db_engine) as session:
                    active_job_ids = Timelapse.find_active_ids(session)

                procs = []
                for job_id in active_job_ids:
                    p = executor.submit(process_job, job_id, settings)
                    procs.append(p)

                for p in concurrent.futures.as_completed(procs):
                    p.result()

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
