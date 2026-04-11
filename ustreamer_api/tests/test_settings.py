import os
import pathlib

from ustreamer_api.settings import get_settings


def test_data_dir_is_created(tmp_path) -> None:
    # pytest injects the built-in tmp_path fixture by matching this parameter name.
    data_dir = tmp_path / "data"
    os.environ["USTREAMER_API_DATA_DIR"] = str(data_dir)

    settings = get_settings()

    assert settings.data_dir == pathlib.Path(data_dir)
    assert data_dir.exists()
    assert data_dir.is_dir()
