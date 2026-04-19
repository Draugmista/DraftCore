from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from draftcore.app.models.enums import OutputFormat, ProjectStatus


DEFAULT_CONFIG_NAME = "draftcore.toml"


class ConfigError(ValueError):
    """Raised when configuration loading or validation fails."""


@dataclass(slots=True)
class WorkspaceSettings:
    root_dir: Path
    assets_dir: Path
    output_dir: Path


@dataclass(slots=True)
class DatabaseSettings:
    path: Path
    echo: bool = False


@dataclass(slots=True)
class DefaultSettings:
    target_output: str = OutputFormat.MARKDOWN.value
    project_status: str = ProjectStatus.ACTIVE.value


@dataclass(slots=True)
class AISettings:
    enabled: bool = False
    provider: str = ""
    model: str = ""
    api_base: str = ""
    api_key_env: str = ""


@dataclass(slots=True)
class LoggingSettings:
    level: str = "INFO"


@dataclass(slots=True)
class AppSettings:
    config_path: Path | None
    workspace: WorkspaceSettings
    database: DatabaseSettings
    defaults: DefaultSettings
    ai: AISettings
    logging: LoggingSettings


def load_settings(
    config_path: str | None = None,
    db_path_override: str | None = None,
    output_dir_override: str | None = None,
) -> AppSettings:
    resolved_config_path = _resolve_config_path(config_path)
    config_data = _read_config(resolved_config_path) if resolved_config_path else {}
    base_dir = resolved_config_path.parent if resolved_config_path else Path.cwd()

    workspace_data = _get_section(config_data, "workspace")
    database_data = _get_section(config_data, "database")
    defaults_data = _get_section(config_data, "defaults")
    ai_data = _get_section(config_data, "ai")
    logging_data = _get_section(config_data, "logging")

    root_dir = _resolve_path(
        workspace_data.get("root_dir", "./data"),
        base_dir=base_dir,
    )
    assets_dir = _resolve_path(
        workspace_data.get("assets_dir", "./samples/assets"),
        base_dir=base_dir,
    )
    output_dir = _resolve_path(
        output_dir_override
        or os.getenv("DRAFTCORE_OUTPUT_DIR")
        or workspace_data.get("output_dir")
        or "./data/outputs",
        base_dir=base_dir,
    )
    database_path = _resolve_path(
        db_path_override
        or os.getenv("DRAFTCORE_DB_PATH")
        or database_data.get("path")
        or "./data/db/draftcore.db",
        base_dir=base_dir,
    )

    defaults = DefaultSettings(
        target_output=str(defaults_data.get("target_output", OutputFormat.MARKDOWN.value)),
        project_status=str(defaults_data.get("project_status", ProjectStatus.ACTIVE.value)),
    )
    _validate_defaults(defaults)

    ai = AISettings(
        enabled=bool(ai_data.get("enabled", False)),
        provider=str(ai_data.get("provider", "")),
        model=str(ai_data.get("model", "")),
        api_base=str(ai_data.get("api_base", "")),
        api_key_env=str(ai_data.get("api_key_env", "")),
    )
    _validate_ai(ai)

    database = DatabaseSettings(
        path=database_path,
        echo=bool(database_data.get("echo", False)),
    )

    return AppSettings(
        config_path=resolved_config_path,
        workspace=WorkspaceSettings(
            root_dir=root_dir,
            assets_dir=assets_dir,
            output_dir=output_dir,
        ),
        database=database,
        defaults=defaults,
        ai=ai,
        logging=LoggingSettings(level=str(logging_data.get("level", "INFO"))),
    )


def _resolve_config_path(config_path: str | None) -> Path | None:
    candidates: list[str | Path | None] = [
        config_path,
        os.getenv("DRAFTCORE_CONFIG"),
        Path.cwd() / DEFAULT_CONFIG_NAME,
        Path.home() / DEFAULT_CONFIG_NAME,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists():
            return path.resolve()
    if config_path:
        raise ConfigError(f"Config file does not exist: {config_path}")
    return None


def _read_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open("rb") as file:
            loaded = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config file is not valid TOML: {config_path}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"Config root must be a table: {config_path}")
    return loaded


def _get_section(config_data: dict[str, Any], name: str) -> dict[str, Any]:
    section = config_data.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"Config section [{name}] must be a table.")
    return section


def _resolve_path(raw_path: str | os.PathLike[str], *, base_dir: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _validate_defaults(defaults: DefaultSettings) -> None:
    if defaults.target_output != OutputFormat.MARKDOWN.value:
        raise ConfigError("Only markdown target_output is supported in the current MVP.")
    try:
        ProjectStatus(defaults.project_status)
    except ValueError as exc:
        raise ConfigError(f"Invalid default project_status: {defaults.project_status}") from exc


def _validate_ai(ai: AISettings) -> None:
    if ai.enabled and (not ai.provider or not ai.model):
        raise ConfigError("AI is enabled but provider/model is incomplete.")
