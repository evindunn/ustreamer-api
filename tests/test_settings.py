import pathlib

from ustreamer_api.settings import get_common_settings, get_worker_settings


def test_data_dir_is_created(monkeypatch, tmp_path) -> None:
    """Common settings initialization creates the configured data directory."""
    data_dir = tmp_path / "data"
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(data_dir))

    settings = get_common_settings()

    assert settings.data_dir == pathlib.Path(data_dir)
    assert data_dir.exists()
    assert data_dir.is_dir()


def test_worker_settings_use_worker_prefix(monkeypatch, tmp_path) -> None:
    """Worker settings read worker-specific environment variables."""
    monkeypatch.setenv("USTREAMER_DATA_DIR", str(tmp_path / "shared-data"))
    monkeypatch.setenv("USTREAMER_DB_FILE", "shared.sqlite")
    monkeypatch.setenv("USTREAMER_WORKER_USTREAMER_URL", "http://camera.local:8080")
    monkeypatch.setenv("USTREAMER_WORKER_LOG_LEVEL", "debug")

    settings = get_worker_settings()

    assert settings.ustreamer_url == "http://camera.local:8080"
    assert settings.log_level == "DEBUG"
