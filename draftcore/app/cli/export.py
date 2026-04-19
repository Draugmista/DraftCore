from __future__ import annotations

import typer

from draftcore.app.cli.support import emit, scaffold_notice

app = typer.Typer(help="Render structured drafts into files.")


@app.command("render")
def render_export(
    ctx: typer.Context,
    draft_id: int = typer.Option(..., "--draft-id", help="Draft identifier."),
    format: str = typer.Option("markdown", "--format", help="Render format."),
    output_path: str = typer.Option(..., "--output-path", help="Output file path."),
) -> None:
    emit(
        ctx,
        "Export render",
        {
            "draft_id": draft_id,
            "format": format,
            "output_path": output_path,
            **scaffold_notice("Export render"),
        },
    )
