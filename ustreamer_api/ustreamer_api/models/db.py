import datetime
import functools
import httpx
import pathlib
import signal
import time
import typing
import uuid
import zoneinfo

from fastapi import Depends
import sqlalchemy
import sqlalchemy.orm
from sqlmodel import Field, SQLModel, create_engine
from .. import settings

UTC = zoneinfo.ZoneInfo("UTC")


def _utc_now() -> datetime.datetime:
    """Return the current time in UTC."""
    return datetime.datetime.now(UTC)


class Timelapse(SQLModel, table=True):
    """Database model representing a timelapse capture session."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    started_at: datetime.datetime = Field(default_factory=_utc_now)
    event_duration: float
    target_duration: float
    target_fps: float
    ended_at: datetime.datetime | None = None

    @property
    def shot_interval(self) -> float:
        """Calculate the interval between shots in seconds."""
        total_frames = self.target_duration * self.target_fps
        return self.event_duration / total_frames

    def execute(self) -> None:
        """Execute the timelapse capture session."""
        stop_requested = False

        def _handle_sigint(signum: int, frame: typing.Any) -> None:
            """Request capture shutdown after the current loop iteration."""
            nonlocal stop_requested
            stop_requested = True

        try:
            config = settings.get_worker_settings()
            output_dir = config.data_dir / f"{self.started_at.strftime('%Y-%m-%dT%H-%M-%S')}_{self.id.hex}"
            output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            started_at = time.monotonic()
            last_capture_at = started_at - self.shot_interval
            frame_index = 0
            previous_sigint_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, _handle_sigint)

            try:
                with httpx.Client(timeout=10.0) as client:
                    while not stop_requested:
                        elapsed = time.monotonic() - started_at
                        if elapsed >= self.event_duration:
                            break

                        if elapsed - (last_capture_at - started_at) >= self.shot_interval:
                            response = client.get(config.ustreamer_url, params={"action": "snapshot"})
                            response.raise_for_status()
                            frame_path = output_dir / f"frame-{frame_index:06d}.jpg"
                            frame_path.write_bytes(response.content)
                            frame_index += 1
                            last_capture_at = time.monotonic()
                            continue

                        time.sleep(min(0.1, self.shot_interval))
            finally:
                signal.signal(signal.SIGINT, previous_sigint_handler)
        finally:
            self.ended_at = _utc_now()

    @staticmethod
    def find_active_ids(session: sqlalchemy.orm.Session) -> list[uuid.UUID]:
        """Return the ids of active timelapses ordered by start time."""
        statement = sqlalchemy.select(Timelapse.id).where(Timelapse.ended_at.is_(None)).order_by(Timelapse.started_at)
        return list(session.execute(statement).scalars())


@functools.cache
def get_engine(db_file: str) -> sqlalchemy.Engine:
    """Create and return a SQLAlchemy engine for the given sqlite database file."""
    if db_file == ":memory:":
        uri = "sqlite://"
        pool_class = sqlalchemy.pool.StaticPool
    else:
        uri = f"sqlite:///{db_file}"
        pool_class = sqlalchemy.pool.QueuePool

    engine = create_engine(
        uri,
        connect_args={"check_same_thread": False},
        poolclass=pool_class,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _get_session(settings: typing.Annotated[settings.APISettings, Depends(settings.get_api_settings)]) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
    """Return a new database session."""
    engine = get_engine(settings.db_file)
    session = sqlalchemy.orm.Session(engine)
    try:
        yield session
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        raise e
    finally:
        session.close()


DatabaseSession = typing.Annotated[sqlalchemy.orm.Session, Depends(_get_session)]
