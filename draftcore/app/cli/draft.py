from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import DraftService

app = typer.Typer(help="Create, update, and inspect drafts.")
draft_service = DraftService()


@app.command("create")
def create_draft(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
    collection_id: int | None = typer.Option(None, "--collection-id", help="Optional collection."),
    reuse_from_latest: bool = typer.Option(
        False,
        "--reuse-from-latest",
        help="Reuse the latest reuse candidates when available.",
    ),
    title: str | None = typer.Option(None, "--title", help="Draft title."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = draft_service.create_draft(
                session,
                project_id=project_id,
                collection_id=collection_id,
                title=title,
            )
        payload["reuse_from_latest"] = reuse_from_latest
        emit(ctx, "Draft created", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("update")
def update_draft(
    ctx: typer.Context,
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
    instructions: str = typer.Option(..., "--instructions", help="Rewrite instructions."),
    use_latest_assets: bool = typer.Option(
        False,
        "--use-latest-assets",
        help="Include the newest project assets in the update.",
    ),
) -> None:
    emit(
        ctx,
        "Draft update",
        {
            "draft_id": draft_id,
            "instructions": instructions,
            "use_latest_assets": use_latest_assets,
            "status": "scaffolded",
            "message": "Draft update is reserved for task 5.",
        },
    )


@app.command("show")
def show_draft(
    ctx: typer.Context,
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            detail = draft_service.get_draft_detail(session, draft_id)
        emit(ctx, "Draft detail", detail)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
