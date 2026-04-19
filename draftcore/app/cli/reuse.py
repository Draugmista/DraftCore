from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Find reusable structures and snippets.")


@app.command("find")
def find_reuse(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="Project identifier."),
    collection_id: int | None = typer.Option(None, "--collection-id", help="Optional collection filter."),
    keywords: str | None = typer.Option(None, "--keywords", help="Search keywords."),
    limit: int = typer.Option(10, "--limit", min=1, help="Maximum candidates to return."),
) -> None:
    emit(
        ctx,
        "Reuse find",
        {
            "project_id": project_id,
            "collection_id": collection_id or "-",
            "keywords": keywords or "-",
            "limit": limit,
            **scaffold_notice("Reuse find"),
        },
    )
