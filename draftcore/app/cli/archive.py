from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import ArchiveService, ValidationError

app = typer.Typer(help="Archive finalized reports.")
archive_service = ArchiveService()


@app.command("finalize")
def finalize_archive(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
    output_path: str | None = typer.Option(None, "--output-path", help="Final output path."),
    name: str = typer.Option(..., "--name", help="Archived report name."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = archive_service.finalize_report(
                session,
                settings,
                project_id=project_id,
                draft_id=draft_id,
                name=name,
                output_path=output_path,
            )
        emit(ctx, "Archive finalize", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("show")
def show_archive(
    ctx: typer.Context,
    report_id: int | None = typer.Option(None, "--report-id", help="Archived report identifier."),
    project_id: int | None = typer.Option(None, "--project-id", help="Project identifier."),
) -> None:
    try:
        if (report_id is None and project_id is None) or (report_id is not None and project_id is not None):
            raise ValidationError("Provide either --report-id or --project-id.")

        settings = get_settings(ctx)
        with session_scope(settings) as session:
            if report_id is not None:
                payload = archive_service.get_report_detail(session, report_id)
            else:
                payload = archive_service.get_latest_project_report_detail(session, project_id)
        emit(ctx, "Archive show", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
