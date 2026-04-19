from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import typer


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


def emit(ctx: typer.Context, title: str, payload: dict[str, Any]) -> None:
    state = get_state(ctx)
    if state.json_output:
        typer.echo(
            json.dumps(
                {
                    "title": title,
                    "payload": payload,
                    "context": asdict(state),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    typer.echo(title)
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")
    if state.verbose:
        typer.echo(
            "context: "
            f"config={state.config or '-'}, "
            f"db_path={state.db_path or '-'}, "
            f"output_dir={state.output_dir or '-'}"
        )


def scaffold_notice(entity: str) -> dict[str, str]:
    return {
        "status": "scaffolded",
        "message": f"{entity} command wiring is ready; service implementation is pending.",
    }
