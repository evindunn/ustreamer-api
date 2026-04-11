import datetime
import functools
import pathlib
import uuid
import zoneinfo

import sqlalchemy
from sqlmodel import Field, SQLModel, create_engine

UTC = zoneinfo.ZoneInfo("UTC")


def _utc_now() -> datetime.datetime:
    """Return the current time in UTC."""
    return datetime.datetime.now(UTC)


class Timelapse(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    started_at: datetime.datetime = Field(default_factory=_utc_now)
    ended_at: datetime.datetime | None = None


@functools.cache
def get_engine(db_file: pathlib.Path) -> sqlalchemy.Engine:
    engine = create_engine(f"sqlite:///{str(db_file.absolute())}")
    SQLModel.metadata.create_all(engine)
    return engine
