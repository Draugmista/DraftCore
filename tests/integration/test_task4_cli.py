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


def _build_collection(db_path: Path, project_id: int, *, name: str = "Q2 Inputs") -> int:
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
            name,
            "--purpose",
            "Review candidate inputs",
        ],
    )
    assert result.exit_code == 0, result.stdout
    return _payload(result)["id"]


def _find_reuse(db_path: Path, project_id: int, *, collection_id: int | None = None) -> None:
    args = [
        "--db-path",
        str(db_path),
        "--json",
        "reuse",
        "find",
        "--project-id",
        str(project_id),
    ]
    if collection_id is not None:
        args.extend(["--collection-id", str(collection_id)])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout


def test_task4_cli_flow_creates_traceable_draft() -> None:
    db_path = _db_path("task4-flow")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    collection_id = _build_collection(db_path, project_id)
    _find_reuse(db_path, project_id)

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
            "--collection-id",
            str(collection_id),
            "--reuse-from-latest",
            "--title",
            "Q2 Main Draft",
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

    assert create_payload["name"] == "Q2 Main Draft"
    assert create_payload["section_count"] == 3
    assert create_payload["generation_mode"] == "template"
    assert create_payload["asset_ref_count"] == 3
    assert create_payload["reuse_ref_count"] == 2
    assert show_payload["source_snapshot"]["collection_id"] == collection_id
    assert [item["candidate_type"] for item in show_payload["reuse_refs"]] == ["structure", "paragraph"]


def test_draft_create_requires_reuse_candidates() -> None:
    db_path = _db_path("task4-missing-reuse")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    _build_collection(db_path, project_id)

    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "draft",
            "create",
            "--project-id",
            str(project_id),
        ],
    )

    assert result.exit_code == 1
    assert "validation error" in result.stderr
    assert "Run reuse find" in result.stderr


def test_draft_create_rejects_existing_main_draft() -> None:
    db_path = _db_path("task4-duplicate")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    _build_collection(db_path, project_id)
    _find_reuse(db_path, project_id)

    first_result = runner.invoke(
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
    assert first_result.exit_code == 0, first_result.stdout

    second_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "draft",
            "create",
            "--project-id",
            str(project_id),
        ],
    )

    assert second_result.exit_code == 1
    assert "validation error" in second_result.stderr
    assert "already has draft" in second_result.stderr


def test_draft_create_requires_explicit_collection_when_multiple_collections_exist() -> None:
    db_path = _db_path("task4-multi-collection")
    project_id = _create_project(db_path)
    _add_assets(db_path, project_id)
    collection_id = _build_collection(db_path, project_id, name="Inputs A")
    _build_collection(db_path, project_id, name="Inputs B")
    _find_reuse(db_path, project_id, collection_id=collection_id)

    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "draft",
            "create",
            "--project-id",
            str(project_id),
        ],
    )

    assert result.exit_code == 1
    assert "validation error" in result.stderr
    assert "multiple collections" in result.stderr
