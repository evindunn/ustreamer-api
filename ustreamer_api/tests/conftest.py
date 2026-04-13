import pytest

from ustreamer_api.models.db import get_engine
from ustreamer_api.settings import get_api_settings, get_worker_settings


@pytest.fixture(autouse=True)
def clear_cached_state() -> None:
    """Reset cached settings and engines around each test."""
    settings = get_api_settings()
    get_api_settings.cache_clear()
    get_worker_settings.cache_clear()

    engine = get_engine(settings.db_file)
    engine.dispose()  # Dispose all engines to release file locks on the database
    get_engine.cache_clear()
    yield
    settings = get_api_settings()
    get_api_settings.cache_clear()
    get_worker_settings.cache_clear()

    engine = get_engine(settings.db_file)
    engine.dispose()  # Dispose all engines to release file locks on the database
    get_engine.cache_clear()
