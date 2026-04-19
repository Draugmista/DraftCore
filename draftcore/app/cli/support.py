from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import typer

from draftcore.app.config.settings import AppSettings, ConfigError, load_settings
from draftcore.app.services.errors import AppError


@dataclass(slots=True)
class CLIState:
    config: str | None
    db_path: str | None
    output_dir: str | None
    json_output: bool
    verbose: bool


def get_state(ctx: typer.Context) -> CLIState:
    state = ctx.obj
    if not isinstance(state, CLIState):
        raise typer.BadParameter("CLI context is not initialized.")
    return state


def get_settings(ctx: typer.Context) -> AppSettings:
    state = get_state(ctx)
    try:
        return load_settings(
            config_path=state.config,
            db_path_override=state.db_path,
            output_dir_override=state.output_dir,
        )
    except ConfigError as exc:
        fail(str(exc), category="config")


def emit(ctx: typer.Context, title: str, payload: dict[str, Any]) -> None:
    state = get_state(ctx)
    normalized = normalize_value(payload)
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "title": title,
                    "payload": normalized,
                    "context": normalize_value(state),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    typer.echo(title)
    for key, value in normalized.items():
        if isinstance(value, (list, dict)):
            typer.echo(f"{key}:")
            typer.echo(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"{key}: {value}")
    if state.verbose:
        typer.echo(
            "context: "
            f"config={state.config or '-'}, "
            f"db_path={state.db_path or '-'}, "
            f"output_dir={state.output_dir or '-'}"
        )


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_value(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: normalize_value(getattr(value, key)) for key in value.__dataclass_fields__}
    return value


def fail(message: str, *, category: str, exit_code: int = 1) -> None:
    typer.echo(f"{category} error: {message}", err=True)
    raise typer.Exit(code=exit_code)


def handle_error(exc: Exception) -> None:
    if isinstance(exc, AppError):
        fail(str(exc), category=exc.category)
    fail(str(exc), category="application")


def scaffold_notice(entity: str) -> dict[str, str]:
    return {
        "status": "scaffolded",
        "message": f"{entity} command wiring is ready; service implementation is pending.",
    }
