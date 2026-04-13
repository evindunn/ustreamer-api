import datetime
import functools
import pathlib
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
    started_at: datetime.datetime = Field(
        default_factory=_utc_now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True), 
            nullable=False
        ),
    )
    event_duration: float
    target_duration: float
    target_fps: float
    ended_at: datetime.datetime | None = None

    @property
    def shot_interval(self) -> float:
        """Calculate the interval between shots in seconds."""
        total_frames = self.target_duration * self.target_fps
        return self.event_duration / total_frames
    
    @property
    def name(self) -> str:
        """Generate a name for the timelapse based on the start time and id."""
        return f"{self.started_at.strftime('%Y-%m-%dT%H-%M-%S')}_{self.id.hex}"

    def image_dir(self, data_dir: pathlib.Path) -> pathlib.Path:
        """Return the directory containing captured frames for this timelapse."""
        return data_dir / self.name

    def output_file(self, data_dir: pathlib.Path) -> pathlib.Path:
        """Return the rendered video path for this timelapse."""
        return data_dir / f"{self.name}.mp4"

    def end(self) -> None:
        """Mark the timelapse as ended by setting the ended_at field to the current time."""
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


def _get_session(settings: typing.Annotated[settings.CommonSettings, Depends(settings.get_common_settings)]) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
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
