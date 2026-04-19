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


def test_task2_cli_flow_builds_collection_context() -> None:
    db_path = _db_path("task2-flow")
    raw_path = Path("samples/assets/workflow-raw-01.md").resolve()
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
            "Quarterly Review",
            "--topic",
            "Q2 performance",
        ],
    )
    assert project_result.exit_code == 0, project_result.stdout
    project_id = _payload(project_result)["id"]

    for source_category, asset_path in [
        ("raw", raw_path),
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
            "Q2 Inputs",
            "--purpose",
            "Review candidate inputs",
        ],
    )
    assert build_result.exit_code == 0, build_result.stdout
    build_payload = _payload(build_result)
    collection_id = build_payload["id"]
    assert build_payload["created"] is True
    assert build_payload["asset_count"] == 3
    assert build_payload["candidate_count"] == 2
    assert build_payload["collected_only_count"] == 1
    assert build_payload["usage_note_coverage"]["ratio"] == 1.0
    assert build_payload["items"][0]["usage_note"] == "background reference"

    show_result = runner.invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--json",
            "collection",
            "show",
            "--collection-id",
            str(collection_id),
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _payload(show_result)
    assert show_payload["id"] == collection_id
    assert show_payload["candidate_count"] == 2
    assert show_payload["collected_only_count"] == 1
    assert [item["source_category"] for item in show_payload["items"]] == [
        "raw",
        "template",
        "reference",
    ]
