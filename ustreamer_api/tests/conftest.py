import pytest

from ustreamer_api.models.db import get_engine
from ustreamer_api.settings import get_settings


@pytest.fixture(autouse=True)
def clear_cached_state() -> None:
    """Reset cached settings and engines around each test."""
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
