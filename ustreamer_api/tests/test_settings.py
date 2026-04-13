import pathlib

from ustreamer_api.settings import get_api_settings, get_worker_settings


def test_data_dir_is_created(monkeypatch, tmp_path) -> None:
    """Settings initialization creates the configured data directory."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("USTREAMER_API_DATA_DIR", str(data_dir))

    settings = get_api_settings()

    assert settings.data_dir == pathlib.Path(data_dir)
    assert data_dir.exists()
    assert data_dir.is_dir()


def test_worker_settings_use_worker_prefix(monkeypatch, tmp_path) -> None:
    """Worker settings read worker-specific environment variables."""
    data_dir = tmp_path / "worker-data"
    monkeypatch.setenv("USTREAMER_WORKER_DATA_DIR", str(data_dir))
    monkeypatch.setenv("USTREAMER_WORKER_DB_FILE", "worker.sqlite")
    monkeypatch.setenv("USTREAMER_WORKER_USTREAMER_URL", "http://camera.local:8080")
    monkeypatch.setenv("USTREAMER_WORKER_LOG_LEVEL", "debug")

    settings = get_worker_settings()

    assert settings.data_dir == pathlib.Path(data_dir)
    assert settings.db_file == "worker.sqlite"
    assert settings.ustreamer_url == "http://camera.local:8080"
    assert settings.log_level == "DEBUG"
