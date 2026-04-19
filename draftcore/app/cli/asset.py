from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Register and inspect assets.")


@app.command("add")
def add_asset(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    path: str = typer.Option(..., "--path", help="Path to the local asset."),
    source_category: str = typer.Option(..., "--source-category", help="Business source category."),
    usage_note: str | None = typer.Option(None, "--usage-note", help="Optional usage note."),
) -> None:
    emit(
        ctx,
        "Asset add",
        {
            "project_id": project_id,
            "path": path,
            "source_category": source_category,
            "usage_note": usage_note or "-",
            **scaffold_notice("Asset add"),
        },
    )


@app.command("list")
def list_assets(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    source_category: str | None = typer.Option(None, "--source-category", help="Optional filter."),
    used_only: bool = typer.Option(False, "--used-only", help="Show only assets already marked used."),
) -> None:
    emit(
        ctx,
        "Asset list",
        {
            "project_id": project_id,
            "source_category": source_category or "all",
            "used_only": used_only,
            **scaffold_notice("Asset list"),
        },
    )


@app.command("show")
def show_asset(
    ctx: typer.Context,
    asset_id: int = typer.Option(..., "--asset-id", help="Asset identifier."),
) -> None:
    emit(
        ctx,
        "Asset show",
        {
            "asset_id": asset_id,
            **scaffold_notice("Asset show"),
        },
    )
