import functools
import logging
import pathlib

import pydantic
import pydantic_settings


def _default_data_dir() -> pathlib.Path:
    """Return the default data directory path."""
    return pathlib.Path.cwd() / ".ustreamer-data"


class CommonSettings(pydantic_settings.BaseSettings):
    """Settings shared by the API server and worker."""
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="USTREAMER_", frozen=True)

    data_dir: pathlib.Path = pydantic.Field(
        default_factory=_default_data_dir,
        description="Directory to store application data, such as the database file and timelapse images/videos",
    )
    db_file: str = pydantic.Field(
        default=":memory:",
        description="Path to the database file. If set to ':memory:', an in-memory database will be used.",
    )

    @pydantic.field_validator("data_dir", mode="after")
    @classmethod
    def _ensure_data_dir_exists(cls, value: pathlib.Path) -> pathlib.Path:
        """Create the data directory if it does not already exist."""
        value.mkdir(parents=True, exist_ok=True)
        return value


class WorkerSettings(pydantic_settings.BaseSettings):
    """Settings used by the background worker."""
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="USTREAMER_WORKER_", frozen=True)

    ustreamer_url: str = pydantic.Field(
        default="http://127.0.0.1:8080",
        description="Base URL of the uStreamer instance to control",
    )

    log_level: str = pydantic.Field(
        default="INFO",
        description="Log level for the worker process.",
    )

    @pydantic.field_validator("log_level", mode="after")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        """Normalize and validate the configured worker log level."""
        normalized_value = value.upper()
        if normalized_value not in logging.getLevelNamesMapping():
            raise ValueError(f"Unsupported worker log level: {value}")
        return normalized_value


@functools.cache
def get_common_settings() -> CommonSettings:
    """Return a cached instance of the common settings."""
    return CommonSettings()


@functools.cache
def get_worker_settings() -> WorkerSettings:
    """Return a cached instance of the worker settings."""
    return WorkerSettings()
