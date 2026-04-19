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


def test_task3_cli_flow_returns_traceable_reuse_candidates() -> None:
    db_path = _db_path("task3-flow")
    template_path = Path("samples/assets/workflow-template-01.md").resolve()
    reference_path = Path("samples/assets/workflow-reference-01.txt").resolve()
    image_path = Path("samples/assets/workflow-image-01.png").resolve()

    project_result = runner.invoke(
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
    assert project_result.exit_code == 0, project_result.stdout
    project_id = _payload(project_result)["id"]

    for source_category, asset_path, usage_note in [
        ("template", template_path, "q2 reusable structure"),
        ("reference", reference_path, "q2 historical evidence"),
        ("template", image_path, None),
    ]:
        add_args = [
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
        ]
        if usage_note:
            add_args.extend(["--usage-note", usage_note])
        add_result = runner.invoke(app, add_args)
        assert add_result.exit_code == 0, add_result.stdout

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

    first_reuse_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "reuse",
            "find",
            "--project-id",
            str(project_id),
            "--limit",
            "3",
        ],
    )
    assert first_reuse_result.exit_code == 0, first_reuse_result.stdout
    first_payload = _payload(first_reuse_result)
    assert first_payload["candidate_count"] == 3
    assert first_payload["degraded_count"] == 1

    second_reuse_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "reuse",
            "find",
            "--project-id",
            str(project_id),
            "--keywords",
            "q2",
            "--limit",
            "2",
        ],
    )
    assert second_reuse_result.exit_code == 0, second_reuse_result.stdout
    second_payload = _payload(second_reuse_result)
    assert second_payload["candidate_count"] == 2
    assert second_payload["template_candidate_count"] == 1
    assert second_payload["reference_candidate_count"] == 1
    assert second_payload["degraded_count"] == 0
    assert [item["candidate_type"] for item in second_payload["items"]] == ["structure", "paragraph"]
    assert all(item["path"] for item in second_payload["items"])
    assert all("reason" in item for item in second_payload["items"])


def test_reuse_find_requires_explicit_collection_when_project_has_multiple_collections() -> None:
    db_path = _db_path("task3-multi-collection")
    template_path = Path("samples/assets/workflow-template-01.md").resolve()
    reference_path = Path("samples/assets/workflow-reference-01.txt").resolve()

    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Collection Selection",
            "--topic",
            "Explicit collection resolution",
        ],
    )
    project_id = _payload(project_result)["id"]

    for source_category, asset_path in [
        ("template", template_path),
        ("reference", reference_path),
    ]:
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

    for name in ["Inputs A", "Inputs B"]:
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
                name,
                "--purpose",
                "Multiple collections",
            ],
        )
        assert build_result.exit_code == 0, build_result.stdout

    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "reuse",
            "find",
            "--project-id",
            str(project_id),
        ],
    )

    assert result.exit_code == 1
    assert "validation error" in result.stderr
    assert "multiple collections" in result.stderr


def test_reuse_find_fails_when_only_path_level_candidates_are_available() -> None:
    db_path = _db_path("task3-path-only")
    template_path = Path("samples/assets/workflow-image-01.png").resolve()
    reference_path = Path("samples/assets/parser-docx-partial-01.docx").resolve()

    project_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "project",
            "create",
            "--name",
            "Fallback Only",
            "--topic",
            "Path-level reuse",
        ],
    )
    project_id = _payload(project_result)["id"]

    for source_category, asset_path in [
        ("template", template_path),
        ("reference", reference_path),
    ]:
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
            "Fallback Inputs",
            "--purpose",
            "Degraded inputs",
        ],
    )
    assert build_result.exit_code == 0, build_result.stdout

    result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "reuse",
            "find",
            "--project-id",
            str(project_id),
        ],
    )

    assert result.exit_code == 1
    assert "validation error" in result.stderr
    assert "Only path-level references" in result.stderr

