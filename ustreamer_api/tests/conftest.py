import os

import pytest

from ustreamer_api.models.db import get_engine
from ustreamer_api.settings import get_common_settings, get_worker_settings


@pytest.fixture(autouse=True)
def clear_cached_state(monkeypatch):
    """Reset cached settings and engines around each test."""
    for env_var in os.environ.keys():
        if env_var.startswith("USTREAMER_"):
            monkeypatch.delenv(env_var, raising=False)

    get_common_settings.cache_clear()
    get_worker_settings.cache_clear()
    get_engine.cache_clear()

    try:
        yield
    finally:
        settings = get_common_settings()
        db = get_engine(settings.db_file)
        get_engine.cache_clear()
        db.dispose()
