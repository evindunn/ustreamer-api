import datetime
import functools
import typing
import uuid
import zoneinfo

from fastapi import Depends
import sqlalchemy
import sqlalchemy.orm
from sqlmodel import Field, SQLModel, create_engine
from ustreamer_api import settings

UTC = zoneinfo.ZoneInfo("UTC")


def _utc_now() -> datetime.datetime:
    """Return the current time in UTC."""
    return datetime.datetime.now(UTC)


class Timelapse(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    started_at: datetime.datetime = Field(default_factory=_utc_now)
    event_duration: float
    timelapse_duration: float
    target_fps: float
    ended_at: datetime.datetime | None = None

    def save(self, session: sqlalchemy.orm.Session) -> None:
        """Save the current state of the timelapse to the database."""
        session.add(self)
        session.commit()
        session.refresh(self)

    def shot_interval(self) -> float:
        """Calculate the interval between shots in seconds."""
        total_frames = self.event_duration * self.target_fps
        return self.timelapse_duration / total_frames

    def end(self) -> None:
        """Mark the timelapse as ended by setting the ended_at timestamp."""
        self.ended_at = _utc_now()


@functools.cache
def get_engine(db_file: str) -> sqlalchemy.Engine:
    if db_file == ":memory:":
        uri = "sqlite://"
    else:
        uri = f"sqlite:///{db_file}"

    engine = create_engine(
        uri,
        connect_args={"check_same_thread": False},
        poolclass=sqlalchemy.pool.StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _get_session(settings: typing.Annotated[settings.Settings, Depends(settings.get_settings)]) -> typing.Generator[sqlalchemy.orm.Session, None, None]:
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
