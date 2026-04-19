from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import ProjectService

app = typer.Typer(help="Manage report projects.")
project_service = ProjectService()


@app.command("create")
def create_project(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", help="Project name."),
    topic: str = typer.Option(..., "--topic", help="Project topic."),
    target_output: str = typer.Option("markdown", "--target-output", help="Target output format."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            project = project_service.create_project(
                session,
                name=name,
                topic=topic,
                target_output=target_output,
                default_status=settings.defaults.project_status,
            )
        emit(
            ctx,
            "Project created",
            {
                "id": project.id,
                "name": project.name,
                "topic": project.topic,
                "target_output": project.target_output,
                "status": project.status,
                "created_at": project.created_at,
            },
        )
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("list")
def list_projects(
    ctx: typer.Context,
    status: str | None = typer.Option(None, "--status", help="Filter by project status."),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of records."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            projects = project_service.list_projects(session, status=status, limit=limit)
        emit(
            ctx,
            "Project list",
            {
                "count": len(projects),
                "items": [
                    {
                        "id": project.id,
                        "name": project.name,
                        "topic": project.topic,
                        "status": project.status,
                        "target_output": project.target_output,
                    }
                    for project in projects
                ],
            },
        )
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("show")
def show_project(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            detail = project_service.get_project_detail(session, project_id)
        emit(ctx, "Project detail", detail)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
