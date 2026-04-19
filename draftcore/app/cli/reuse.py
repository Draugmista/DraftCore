from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import ReuseService

app = typer.Typer(help="Find reusable structures and snippets.")
reuse_service = ReuseService()


@app.command("find")
def find_reuse(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
    collection_id: int | None = typer.Option(None, "--collection-id", help="Optional collection filter."),
    keywords: str | None = typer.Option(None, "--keywords", help="Search keywords."),
    limit: int = typer.Option(10, "--limit", min=1, help="Maximum candidates to return."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = reuse_service.find_reuse(
                session,
                project_id=project_id,
                collection_id=collection_id,
                keywords=keywords,
                limit=limit,
            )
        emit(ctx, "Reuse find", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
