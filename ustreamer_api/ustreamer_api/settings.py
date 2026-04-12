import functools
import pathlib

import pydantic
import pydantic_settings


def _default_data_dir() -> pathlib.Path:
    """Return the default data directory path."""
    return pathlib.Path.cwd() / ".ustreamer-data"


class Settings(pydantic_settings.BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="USTREAMER_API_", frozen=True)

    data_dir: pathlib.Path = pydantic.Field(
        default_factory=_default_data_dir,
        description="Directory to store application data, such as the database file and timelapse images/videos",
    )
    db_file: str = pydantic.Field(
        default=":memory:",
        description="Path to the database file. If set to ':memory:', an in-memory database will be used.",
    )
    ustreamer_url: str = pydantic.Field(
        default="http://127.0.0.1:8080",
        description="Base URL of the uStreamer instance to control",
    )

    @pydantic.field_validator("data_dir", mode="after")
    @classmethod
    def _ensure_data_dir_exists(cls, value: pathlib.Path) -> pathlib.Path:
        """Create the data directory if it does not already exist."""
        value.mkdir(parents=True, exist_ok=True)
        return value


@functools.cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings()
