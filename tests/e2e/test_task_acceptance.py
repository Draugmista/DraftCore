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


def _expected(name: str) -> dict:
    return json.loads((Path("samples/expected") / name).read_text(encoding="utf-8"))


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".test-db" / f"{name}-{uuid4().hex}.db").resolve()


def _create_project(db_path: Path) -> int:
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
    return _payload(create_result)["id"]


def _add_assets(db_path: Path, project_id: int) -> None:
    fixtures = [
        ("raw", Path("samples/assets/workflow-raw-01.md").resolve()),
        ("template", Path("samples/assets/workflow-template-01.md").resolve()),
        ("reference", Path("samples/assets/workflow-reference-01.txt").resolve()),
    ]
    for source_category, asset_path in fixtures:
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
                source_category,
            ],
        )
        assert add_result.exit_code == 0, add_result.stdout


def test_task1_acceptance_project_scope() -> None:
    expected = _expected("acceptance-task1-01.json")
    db_path = _db_path("e2e-task1")

    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)

    show_result = runner.invoke(
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
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)

    list_result = runner.invoke(
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
    assert list_result.exit_code == 0, list_result.stdout
    list_payload = _payload(list_result)

    assert show_payload["target_output"] == expected["project"]["target_output"]
    assert show_payload["status"] == expected["project"]["status"]
    assert show_payload["asset_count"] == expected["project_scope"]["asset_count"]
    assert sorted(item["source_category"] for item in list_payload["items"]) == sorted(
        expected["project_scope"]["source_categories"]
    )


def test_task2_acceptance_collection_context() -> None:
    expected = _expected("acceptance-task2-01.json")
    db_path = _db_path("e2e-task2")

    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)

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
    build_payload = _payload(build_result)

    show_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "collection",
            "show",
            "--collection-id",
            str(build_payload["id"]),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)

    assert show_payload["asset_count"] == expected["collection"]["asset_count"]
    assert show_payload["candidate_count"] == expected["collection"]["candidate_count"]
    assert show_payload["collected_only_count"] == expected["collection"]["collected_only_count"]
    assert show_payload["usage_note_coverage"]["ratio"] == expected["collection"][
        "usage_note_coverage_ratio"
    ]
    assert [
        {
            "source_category": item["source_category"],
            "usage_note": item["usage_note"],
            "is_candidate": item["is_candidate"],
        }
        for item in show_payload["items"]
    ] == expected["items"]
