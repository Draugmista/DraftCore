from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, get_settings, handle_error
from draftcore.app.db import session_scope
from draftcore.app.services import AssetService

app = typer.Typer(help="Register and inspect assets.")
asset_service = AssetService()


@app.command("add")
def add_asset(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    path: str = typer.Option(..., "--path", help="Path to the local asset."),
    source_category: str = typer.Option(..., "--source-category", help="Business source category."),
    usage_note: str | None = typer.Option(None, "--usage-note", help="Optional usage note."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            detail = asset_service.add_asset(
                session,
                project_id=project_id,
                path=path,
                source_category=source_category,
                usage_note=usage_note,
            )
        emit(ctx, "Asset registered", detail)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("list")
def list_assets(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    source_category: str | None = typer.Option(None, "--source-category", help="Optional filter."),
    used_only: bool = typer.Option(False, "--used-only", help="Show only assets already marked used."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = asset_service.list_project_assets(
                session,
                project_id=project_id,
                source_category=source_category,
                used_only=used_only,
            )
        emit(ctx, "Asset list", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)


@app.command("show")
def show_asset(
    ctx: typer.Context,
    asset_id: int = typer.Option(..., "--asset-id", help="Asset identifier."),
) -> None:
    try:
        settings = get_settings(ctx)
        with session_scope(settings) as session:
            payload = asset_service.get_asset_detail(session, asset_id)
        emit(ctx, "Asset detail", payload)
    except Exception as exc:  # pragma: no cover - exercised in CLI tests
        handle_error(exc)
