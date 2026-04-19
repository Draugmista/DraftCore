from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Manage report projects.")


@app.command("create")
def create_project(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Project name."),
    topic: str = typer.Option(..., "--topic", help="Project topic."),
    target_output: str = typer.Option("markdown", "--target-output", help="Target output format."),
) -> None:
    emit(
        ctx,
        "Project create",
        {
            "name": name,
            "topic": topic,
            "target_output": target_output,
            **scaffold_notice("Project create"),
        },
    )


@app.command("list")
def list_projects(
    ctx: typer.Context,
    status: str | None = typer.Option(None, "--status", help="Filter by project status."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of records."),
) -> None:
    emit(
        ctx,
        "Project list",
        {
            "status_filter": status or "all",
            "limit": limit,
            **scaffold_notice("Project list"),
        },
    )


@app.command("show")
def show_project(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
) -> None:
    emit(
        ctx,
        "Project show",
        {
            "project_id": project_id,
            **scaffold_notice("Project show"),
        },
    )
