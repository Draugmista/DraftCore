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


def _add_late_asset(db_path: Path, project_id: int) -> None:
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
            str(Path("samples/assets/workflow-raw-02.md").resolve()),
            "--source-category",
            "raw",
            "--usage-note",
            "late evidence",
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


def test_task4_acceptance_main_draft_generation() -> None:
    expected = _expected("acceptance-task4-01.json")
    db_path = _db_path("e2e-task4")

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
    collection_id = _payload(build_result)["id"]

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
    create_payload = _payload(create_result)

    show_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "draft",
            "show",
            "--draft-id",
            str(create_payload["id"]),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)

    assert create_payload["section_count"] == expected["draft"]["section_count"]
    assert create_payload["generation_mode"] == expected["draft"]["generation_mode"]
    assert create_payload["asset_ref_count"] == expected["draft"]["asset_ref_count"]
    assert create_payload["reuse_ref_count"] == expected["draft"]["reuse_ref_count"]
    assert show_payload["source_snapshot"]["collection_id"] == collection_id
    assert [section["heading"] for section in show_payload["content_model"]["sections"]] == expected["section_headings"]
    assert [item["source_category"] for item in show_payload["reuse_refs"]] == expected["reuse_ref_categories"]


def test_task5_acceptance_main_draft_update() -> None:
    expected = _expected("acceptance-task5-01.json")
    db_path = _db_path("e2e-task5")

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
    created_payload = _payload(create_result)

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
            str(created_payload["id"]),
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
            str(created_payload["id"]),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)

    assert update_payload["version_label"] == expected["draft"]["version_label"]
    assert update_payload["status"] == expected["draft"]["status"]
    assert update_payload["asset_ref_count"] == expected["draft"]["asset_ref_count"]
    assert update_payload["assets_added_count"] == expected["draft"]["assets_added_count"]
    assert update_payload["revision_count"] == expected["draft"]["revision_count"]
    assert update_payload["updated_section_count"] == expected["draft"]["updated_section_count"]
    assert show_payload["last_revision"]["changed_sections"] == expected["changed_sections"]
    assert show_payload["status"] == expected["draft"]["status"]
