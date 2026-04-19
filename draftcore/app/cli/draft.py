from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Create, update, and inspect drafts.")


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
    emit(
        ctx,
        "Draft create",
        {
            "project_id": project_id,
            "collection_id": collection_id or "-",
            "reuse_from_latest": reuse_from_latest,
            "title": title or "-",
            **scaffold_notice("Draft create"),
        },
    )


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
            **scaffold_notice("Draft update"),
        },
    )


@app.command("show")
def show_draft(
    ctx: typer.Context,
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
) -> None:
    emit(
        ctx,
        "Draft show",
        {
            "draft_id": draft_id,
            **scaffold_notice("Draft show"),
        },
    )
