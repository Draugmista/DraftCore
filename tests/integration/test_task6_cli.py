from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from draftcore.app.cli import app


runner = CliRunner()


def _payload(result) -> dict:
    body = json.loads(result.stdout)
    return body["payload"]


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".test-db" / f"{name}-{uuid4().hex}.db").resolve()


def _output_dir(name: str) -> Path:
    return (Path.cwd() / ".test-output" / f"{name}-{uuid4().hex}").resolve()


def _create_project(db_path: Path) -> int:
    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Quarterly Review",
            "--topic",
            "Q2 performance",
        ],
    )
    assert result.exit_code == 0, result.stdout
    return _payload(result)["id"]


def _add_assets(db_path: Path, project_id: int) -> None:
    for source_category, filename in [
        ("raw", "workflow-raw-01.md"),
        ("template", "workflow-template-01.md"),
        ("reference", "workflow-reference-01.txt"),
    ]:
        result = runner.invoke(
            app,
            [
                "--db-path",
                str(db_path),
                "--json",
                "asset",
                "add",
                "--project-id",
                str(project_id),
                "--path",
                str(Path("samples/assets", filename).resolve()),
                "--source-category",
                source_category,
            ],
        )
        assert result.exit_code == 0, result.stdout


def _prepare_ready_draft(db_path: Path, project_id: int) -> int:
    build_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "collection",
            "build",
            "--project-id",
            str(project_id),
            "--name",
            "Q2 Inputs",
            "--purpose",
            "Review candidate inputs",
        ],
    )
    assert build_result.exit_code == 0, build_result.stdout

    reuse_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "reuse",
            "find",
            "--project-id",
            str(project_id),
        ],
    )
    assert reuse_result.exit_code == 0, reuse_result.stdout

    create_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "create",
            "--project-id",
            str(project_id),
        ],
    )
    assert create_result.exit_code == 0, create_result.stdout
    draft_id = _payload(create_result)["id"]

    update_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "update",
            "--draft-id",
            str(draft_id),
            "--instructions",
            "整理已有内容并统一表达",
        ],
    )
    assert update_result.exit_code == 0, update_result.stdout
    return draft_id


def test_task6_cli_flow_exports_and_archives_latest_report() -> None:
    db_path = _db_path("task6-flow")
    output_dir = _output_dir("task6-flow")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    draft_id = _prepare_ready_draft(db_path, project_id)

    export_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--output-dir",
            str(output_dir),
            "--json",
            "export",
            "render",
            "--draft-id",
            str(draft_id),
        ],
    )
    assert export_result.exit_code == 0, export_result.stdout
    export_payload = _payload(export_result)

    finalize_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--output-dir",
            str(output_dir),
            "--json",
            "archive",
            "finalize",
            "--project-id",
            str(project_id),
            "--draft-id",
            str(draft_id),
            "--name",
            "Quarterly Review Final",
        ],
    )
    assert finalize_result.exit_code == 0, finalize_result.stdout
    finalize_payload = _payload(finalize_result)

    show_latest_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "archive",
            "show",
            "--project-id",
            str(project_id),
        ],
    )
    assert show_latest_result.exit_code == 0, show_latest_result.stdout
    show_latest_payload = _payload(show_latest_result)

    show_report_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "archive",
            "show",
            "--report-id",
            str(finalize_payload["id"]),
        ],
    )
    assert show_report_result.exit_code == 0, show_report_result.stdout
    show_report_payload = _payload(show_report_result)

    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "show",
            "--project-id",
            str(project_id),
        ],
    )
    assert project_result.exit_code == 0, project_result.stdout
    project_payload = _payload(project_result)

    add_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "asset",
            "add",
            "--project-id",
            str(project_id),
            "--path",
            finalize_payload["output_path"],
            "--source-category",
            "reference",
            "--usage-note",
            "archived report for reuse",
        ],
    )
    assert add_result.exit_code == 0, add_result.stdout
    add_payload = _payload(add_result)

    assert Path(export_payload["output_path"]).exists()
    assert Path(finalize_payload["output_path"]).exists()
    assert finalize_payload["id"] == show_latest_payload["id"] == show_report_payload["id"]
    assert finalize_payload["output_format"] == "markdown"
    assert finalize_payload["asset_ref_count"] >= 1
    assert finalize_payload["reuse_ref_count"] >= 1
    assert project_payload["draft_status"] == "archived"
    assert project_payload["final_report_status"] == "archived"
    assert add_payload["source_category"] == "reference"
    assert Path(add_payload["path"]).resolve() == Path(finalize_payload["output_path"]).resolve()


def test_archive_show_requires_exactly_one_lookup_argument() -> None:
    db_path = _db_path("task6-show-validation")

    missing_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "archive",
            "show",
        ],
    )
    both_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "archive",
            "show",
            "--report-id",
            "1",
            "--project-id",
            "1",
        ],
    )

    assert missing_result.exit_code == 1
    assert "validation error" in missing_result.stderr
    assert "either --report-id or --project-id" in missing_result.stderr
    assert both_result.exit_code == 1
    assert "validation error" in both_result.stderr
