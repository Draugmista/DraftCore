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


def _build_collection(db_path: Path, project_id: int) -> int:
    result = runner.invoke(
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
    assert result.exit_code == 0, result.stdout
    return _payload(result)["id"]


def _find_reuse(db_path: Path, project_id: int) -> None:
    result = runner.invoke(
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
    assert result.exit_code == 0, result.stdout


def _create_draft(db_path: Path, project_id: int) -> dict:
    result = runner.invoke(
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
    assert result.exit_code == 0, result.stdout
    return _payload(result)


def _add_late_asset(db_path: Path, project_id: int) -> None:
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
            str(Path("samples/assets", "workflow-raw-02.md").resolve()),
            "--source-category",
            "raw",
            "--usage-note",
            "late evidence",
        ],
    )
    assert result.exit_code == 0, result.stdout


def test_task5_cli_flow_updates_main_draft_in_place() -> None:
    db_path = _db_path("task5-flow")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    _build_collection(db_path, project_id)
    _find_reuse(db_path, project_id)
    created = _create_draft(db_path, project_id)
    _add_late_asset(db_path, project_id)

    update_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "update",
            "--draft-id",
            str(created["id"]),
            "--instructions",
            "补充新增素材并统一表达",
            "--use-latest-assets",
        ],
    )
    assert update_result.exit_code == 0, update_result.stdout
    update_payload = _payload(update_result)

    show_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "show",
            "--draft-id",
            str(created["id"]),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)

    assert update_payload["id"] == created["id"]
    assert update_payload["previous_version_label"] == "v1"
    assert update_payload["version_label"] == "v2"
    assert update_payload["status"] == "ready"
    assert update_payload["asset_ref_count"] == 4
    assert update_payload["assets_added_count"] == 1
    assert update_payload["revision_count"] == 1
    assert show_payload["revision_count"] == 1
    assert show_payload["last_revision"]["new_version_label"] == "v2"
    assert show_payload["last_revision"]["assets_added"] != []
    assert show_payload["asset_ref_count"] == 4
    assert show_payload["status"] == "ready"


def test_draft_update_keeps_incrementing_versions() -> None:
    db_path = _db_path("task5-repeat-update")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    _build_collection(db_path, project_id)
    _find_reuse(db_path, project_id)
    created = _create_draft(db_path, project_id)

    first_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "update",
            "--draft-id",
            str(created["id"]),
            "--instructions",
            "整理已有内容",
        ],
    )
    assert first_result.exit_code == 0, first_result.stdout
    first_payload = _payload(first_result)

    second_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "update",
            "--draft-id",
            str(created["id"]),
            "--instructions",
            "统一表达",
        ],
    )
    assert second_result.exit_code == 0, second_result.stdout
    second_payload = _payload(second_result)

    assert first_payload["version_label"] == "v2"
    assert second_payload["previous_version_label"] == "v2"
    assert second_payload["version_label"] == "v3"
    assert second_payload["revision_count"] == 2
