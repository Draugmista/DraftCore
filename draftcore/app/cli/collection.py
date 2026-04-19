from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Build and inspect asset collections.")


@app.command("build")
def build_collection(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Owning project identifier."),
    name: str = typer.Option(..., "--name", help="Collection name."),
    purpose: str = typer.Option(..., "--purpose", help="Collection purpose."),
) -> None:
    emit(
        ctx,
        "Collection build",
        {
            "project_id": project_id,
            "name": name,
            "purpose": purpose,
            **scaffold_notice("Collection build"),
        },
    )


@app.command("show")
def show_collection(
    ctx: typer.Context,
    collection_id: int = typer.Option(..., "--collection-id", help="Collection identifier."),
) -> None:
    emit(
        ctx,
        "Collection show",
        {
            "collection_id": collection_id,
            **scaffold_notice("Collection show"),
        },
    )
