import concurrent.futures
import logging
import multiprocessing
import random
import time
import uuid

import sqlalchemy
import sqlalchemy.orm

from .settings import Settings
from .models.db import get_engine, Timelapse


base_logger = logging.getLogger(__package__)


def _get_db_engine(settings: Settings) -> sqlalchemy.Engine:
    """Create and return a new database session."""
    return get_engine(settings.db_file)


def process_job(job_id: uuid.UUID, settings: Settings) -> uuid.UUID:
    """Fetch a the job with the given id from the database and start generating the timelapse frames."""
    db_engine = _get_db_engine(settings)
    with sqlalchemy.orm.Session(db_engine) as session:
        timelapse = session.get(Timelapse, job_id)
        if timelapse is not None:
            print(f"Processing job {job_id}...")
        else:
            print(f"Job {job_id} not found in the database")
            return job_id
        
    time.sleep(random.randint(1, 3))  # Simulate the time taken to process the job
    print(f"Finished processing job {job_id}")
    return job_id


def worker_main():
    """Worker process function to perform background tasks."""
    settings = Settings()
    db_engine = _get_db_engine(settings)

    with concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        while True:
            frame_start = time.time()
            with sqlalchemy.orm.Session(db_engine) as session:
                active_job_ids = Timelapse.find_active_ids(session)
            
            procs = []
            for job_id in active_job_ids:
                p = executor.submit(process_job, job_id, settings)
                procs.append(p)

            with sqlalchemy.orm.Session(db_engine) as session:
                for p in procs:
                    job_id = p.result()  # Wait for all submitted jobs to complete before starting the next frame
                    base_logger.info(f"Job {job_id} completed with result")

                    job = session.get(Timelapse, job_id)
                    if job is None:
                        base_logger.warning(f"Job {job_id} not found in the database after processing")
                    else:
                        job.done()
                        session.add(job)
                session.commit()

            frame_duration = time.time() - frame_start
            time.sleep(1.0 - frame_duration)
