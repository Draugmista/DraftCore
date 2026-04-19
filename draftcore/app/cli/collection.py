from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import CollectionService

app = typer.Typer(help="Build and inspect asset collections.")
collection_service = CollectionService()


@app.command("build")
def build_collection(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    name: str = typer.Option(..., "--name", help="Collection name."),
    purpose: str = typer.Option(..., "--purpose", help="Collection purpose."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = collection_service.build_collection(
                session,
                project_id=project_id,
                name=name,
                purpose=purpose,
            )
        emit(ctx, "Collection build", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("show")
def show_collection(
    ctx: typer.Context,
    collection_id: int = typer.Option(..., "--collection-id", help="Collection identifier."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = collection_service.get_collection_detail(session, collection_id)
        emit(ctx, "Collection show", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
