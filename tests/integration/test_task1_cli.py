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


def test_task1_cli_flow() -> None:
    db_path = _db_path("task1-flow")
    asset_path = Path("samples/assets/workflow-raw-01.md").resolve()

    create_result = runner.invoke(
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
    assert create_result.exit_code == 0, create_result.stdout
    project_payload = _payload(create_result)
    project_id = project_payload["id"]
    assert project_payload["status"] == "active"

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
            str(asset_path),
            "--source-category",
            "raw",
            "--usage-note",
            "background reference",
        ],
    )
    assert add_result.exit_code == 0, add_result.stdout
    asset_payload = _payload(add_result)
    asset_id = asset_payload["id"]
    assert asset_payload["project_id"] == project_id
    assert asset_payload["ingestion_status"] == "parsed"
    assert asset_payload["profile"]["summary"]

    list_result = runner.invoke(
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
    assert list_result.exit_code == 0, list_result.stdout
    detail_payload = _payload(list_result)
    assert detail_payload["asset_count"] == 1
    assert detail_payload["draft_status"] == "not_started"

    asset_list_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "asset",
            "list",
            "--project-id",
            str(project_id),
        ],
    )
    assert asset_list_result.exit_code == 0, asset_list_result.stdout
    list_payload = _payload(asset_list_result)
    assert list_payload["asset_count"] == 1
    assert list_payload["items"][0]["id"] == asset_id

    show_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "asset",
            "show",
            "--asset-id",
            str(asset_id),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)
    assert show_payload["projects"][0]["project_id"] == project_id


def test_asset_add_reuses_existing_asset_for_same_path() -> None:
    db_path = _db_path("reuse-same-path")
    shared_path = Path("samples/assets/workflow-template-01.md").resolve()

    first_project = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Project One",
            "--topic",
            "Topic One",
        ],
    )
    second_project = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Project Two",
            "--topic",
            "Topic Two",
        ],
    )
    first_project_id = _payload(first_project)["id"]
    second_project_id = _payload(second_project)["id"]

    first_add = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "asset",
            "add",
            "--project-id",
            str(first_project_id),
            "--path",
            str(shared_path),
            "--source-category",
            "template",
        ],
    )
    second_add = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "asset",
            "add",
            "--project-id",
            str(second_project_id),
            "--path",
            str(shared_path),
            "--source-category",
            "template",
        ],
    )

    first_payload = _payload(first_add)
    second_payload = _payload(second_add)
    assert first_payload["id"] == second_payload["id"]
    assert first_payload["created"] is True
    assert second_payload["created"] is False


def test_asset_add_degrades_when_docx_cannot_be_parsed() -> None:
    db_path = _db_path("broken-docx")
    broken_docx = Path("samples/assets/parser-docx-partial-01.docx").resolve()

    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Broken Input",
            "--topic",
            "Fallback behavior",
        ],
    )
    project_id = _payload(project_result)["id"]

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
            str(broken_docx),
            "--source-category",
            "reference",
        ],
    )

    assert add_result.exit_code == 0, add_result.stdout
    payload = _payload(add_result)
    assert payload["ingestion_status"] == "failed"
    assert payload["profile"]["summary"] == "Asset metadata was recorded, but content extraction failed."


def test_asset_add_rejects_source_category_switch_for_same_file() -> None:
    db_path = _db_path("category-switch")
    shared_path = Path("samples/assets/workflow-template-01.md").resolve()

    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Category Switch",
            "--topic",
            "Guard global asset semantics",
        ],
    )
    project_id = _payload(project_result)["id"]

    first_add = runner.invoke(
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
            str(shared_path),
            "--source-category",
            "template",
        ],
    )
    assert first_add.exit_code == 0, first_add.stdout

    second_add = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "asset",
            "add",
            "--project-id",
            str(project_id),
            "--path",
            str(shared_path),
            "--source-category",
            "raw",
        ],
    )

    assert second_add.exit_code == 1
    assert "validation error" in second_add.stderr
    assert "cannot switch" in second_add.stderr


def test_asset_list_used_only_is_not_available_yet() -> None:
    db_path = _db_path("used-only")
    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Used Filter",
            "--topic",
            "Unsupported flag",
        ],
    )
    project_id = _payload(project_result)["id"]

    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "asset",
            "list",
            "--project-id",
            str(project_id),
            "--used-only",
        ],
    )

    assert result.exit_code == 1
    assert "unsupported error" in result.stderr
