from __future__ import annotations

import typer

from draftcore.app.cli import archive, asset, collection, draft, export, project, reuse
from draftcore.app.cli.support import CLIState

app = typer.Typer(
    name="draftcore",
    no_args_is_help=True,
    help="DraftCore local-first CLI for personal report workflows.",
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: str | None = typer.Option(
        None,
        "--config",
        help="Path to the DraftCore TOML configuration file.",
    ),
    db_path: str | None = typer.Option(
        None,
        "--db-path",
        help="Override the SQLite database path.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        help="Override the default output directory.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON output.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose CLI diagnostics.",
    ),
) -> None:
    """Initialize the CLI context shared by all command groups."""

    ctx.obj = CLIState(
        config=config,
        db_path=db_path,
        output_dir=output_dir,
        json_output=json_output,
        verbose=verbose,
    )


app.add_typer(project.app, name="project")
app.add_typer(asset.app, name="asset")
app.add_typer(collection.app, name="collection")
app.add_typer(reuse.app, name="reuse")
app.add_typer(draft.app, name="draft")
app.add_typer(export.app, name="export")
app.add_typer(archive.app, name="archive")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
