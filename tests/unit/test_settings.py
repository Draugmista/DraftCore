from pathlib import Path

from draftcore.app.config.settings import AppSettings, load_settings


def test_load_settings_uses_defaults_without_config() -> None:
    settings = load_settings()

    assert settings == AppSettings()


def test_load_settings_accepts_config_path() -> None:
    config_path = "configs/local.toml"

    settings = load_settings(config_path)

    assert settings.config_path == Path(config_path)
    assert settings.db_path == Path("draftcore.db")
    assert settings.output_dir == Path("output")
