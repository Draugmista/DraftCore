from __future__ import annotations

from pathlib import Path

import pytest

from draftcore.app.config.settings import ConfigError, load_settings


def test_load_settings_prefers_overrides_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = Path("tests/fixtures/config-valid.toml").resolve()
    monkeypatch.setenv("DRAFTCORE_DB_PATH", str((Path.cwd() / ".test-db" / "env.db").resolve()))

    settings = load_settings(
        config_path=str(config_path),
        db_path_override=str((Path.cwd() / ".test-db" / "override.db").resolve()),
        output_dir_override=str((Path.cwd() / ".test-output").resolve()),
    )

    assert settings.database.path == (Path.cwd() / ".test-db" / "override.db").resolve()
    assert settings.workspace.output_dir == (Path.cwd() / ".test-output").resolve()
    assert settings.database.echo is True


def test_load_settings_rejects_non_markdown_target_output() -> None:
    with pytest.raises(ConfigError):
        load_settings(config_path=str(Path("tests/fixtures/config-invalid-output.toml").resolve()))
