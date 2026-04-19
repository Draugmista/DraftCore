from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import ExportService

app = typer.Typer(help="Render structured drafts into files.")
export_service = ExportService()


@app.command("render")
def render_export(
    ctx: typer.Context,
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
    format: str = typer.Option("markdown", "--format", help="Render format."),
    output_path: str | None = typer.Option(None, "--output-path", help="Output file path."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = export_service.render_draft(
                session,
                settings,
                draft_id=draft_id,
                output_format=format,
                output_path=output_path,
            )
        emit(ctx, "Export render", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
