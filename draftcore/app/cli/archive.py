from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Archive finalized reports.")


@app.command("finalize")
def finalize_archive(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
    output_path: str = typer.Option(..., "--output-path", help="Final output path."),
    name: str = typer.Option(..., "--name", help="Archived report name."),
) -> None:
    emit(
        ctx,
        "Archive finalize",
        {
            "project_id": project_id,
            "draft_id": draft_id,
            "output_path": output_path,
            "name": name,
            **scaffold_notice("Archive finalize"),
        },
    )


@app.command("show")
def show_archive(
    ctx: typer.Context,
    report_id: int | None = typer.Option(None, "--report-id", help="Archived report identifier."),
    project_id: int | None = typer.Option(None, "--project-id", help="Project identifier."),
) -> None:
    emit(
        ctx,
        "Archive show",
        {
            "report_id": report_id or "-",
            "project_id": project_id or "-",
            **scaffold_notice("Archive show"),
        },
    )
