import functools
import pathlib

import pydantic
import pydantic_settings


def _default_data_dir() -> pathlib.Path:
    """Return the default data directory path."""
    return pathlib.Path.cwd() / ".ustreamer-data"


class Settings(pydantic_settings.BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="USTREAMER_API_")

    data_dir: pathlib.Path = pydantic.Field(
        default_factory=_default_data_dir,
        description="Directory to store application data, such as the database file and timelapse images/videos",
    )

    @pydantic.field_validator("data_dir", mode="after")
    @classmethod
    def _ensure_data_dir_exists(cls, value: pathlib.Path) -> pathlib.Path:
        """Create the data directory if it does not already exist."""
        value.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def db_file(self) -> pathlib.Path:
        """Return the path to the database file."""
        return self.data_dir / "ustreamer-api.sqlite"


@functools.cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings()
