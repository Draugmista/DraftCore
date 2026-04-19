from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import delete, select

from draftcore.app.config.settings import load_settings
from draftcore.app.db import session_scope
from draftcore.app.exporters import MarkdownExporter
from draftcore.app.models import Draft, DraftAssetRef, DraftReuseRef, FinalReport, FinalReportAssetRef, FinalReportReuseRef
from draftcore.app.models.enums import DraftStatus
from draftcore.app.services import ArchiveService, AssetService, CollectionService, DraftService, ExportService, ProjectService, ReuseService
from draftcore.app.services.errors import ValidationError


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".pytest-tmp" / f"{name}-{uuid4().hex}.db").resolve()


def _output_dir(name: str) -> Path:
    return (Path.cwd() / ".pytest-tmp" / f"{name}-{uuid4().hex}").resolve()


def _settings(name: str):
    return load_settings(
        db_path_override=str(_db_path(name)),
        output_dir_override=str(_output_dir(name)),
    )


def _create_project(session, *, name: str = "Quarterly Review", topic: str = "Q2 performance") -> int:
    project = ProjectService().create_project(
        session,
        name=name,
        topic=topic,
        target_output="markdown",
        default_status="active",
    )
    assert project.id is not None
    return project.id


def _prepare_ready_draft(session) -> tuple[int, int]:
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()
    draft_service = DraftService()

    project_id = _create_project(session)
    for source_category, filename in [
        ("raw", "workflow-raw-01.md"),
        ("template", "workflow-template-01.md"),
        ("reference", "workflow-reference-01.txt"),
    ]:
        asset_service.add_asset(
            session,
            project_id=project_id,
            path=str(Path("samples/assets", filename).resolve()),
            source_category=source_category,
        )
    collection = collection_service.build_collection(
        session,
        project_id=project_id,
        name="Q2 Inputs",
        purpose="Review candidate inputs",
    )
    reuse_service.find_reuse(session, project_id=project_id)
    created = draft_service.create_draft(session, project_id=project_id, collection_id=collection["id"])
    updated = draft_service.update_draft(
        session,
        draft_id=created["id"],
        instructions="整理已有内容并统一表达",
    )
    return project_id, updated["id"]


def test_markdown_exporter_renders_title_sections_and_blocks() -> None:
    exporter = MarkdownExporter()

    rendered = exporter.render(
        {
            "title": "Q2 Main Draft",
            "sections": [
                {
                    "heading": "Background",
                    "blocks": [
                        {"type": "text", "text": "Line A", "source_refs": {"asset_ids": [1], "reuse_candidate_ids": []}},
                        {"type": "text", "text": "Line B", "source_refs": {"asset_ids": [2], "reuse_candidate_ids": []}},
                    ],
                }
            ],
        }
    )

    assert rendered == "# Q2 Main Draft\n\n## Background\n\nLine A\n\nLine B\n"


def test_export_render_writes_markdown_to_default_output_dir() -> None:
    settings = _settings("export-default-path")
    export_service = ExportService()

    with session_scope(settings) as session:
        _, draft_id = _prepare_ready_draft(session)
        payload = export_service.render_draft(
            session,
            settings,
            draft_id=draft_id,
            output_format="markdown",
        )

    output_path = payload["output_path"]
    assert output_path.exists()
    assert output_path.name.startswith(f"1-{draft_id}-")
    assert output_path.suffix == ".md"
    assert "# Quarterly Review Draft" in output_path.read_text(encoding="utf-8")


def test_archive_finalize_persists_final_report_and_trace_refs() -> None:
    settings = _settings("archive-finalize")
    archive_service = ArchiveService()

    with session_scope(settings) as session:
        project_id, draft_id = _prepare_ready_draft(session)
        payload = archive_service.finalize_report(
            session,
            settings,
            project_id=project_id,
            draft_id=draft_id,
            name="Quarterly Review Final",
        )
        stored_report = session.exec(select(FinalReport).where(FinalReport.draft_id == draft_id)).first()
        asset_refs = list(
            session.exec(
                select(FinalReportAssetRef).where(FinalReportAssetRef.final_report_id == stored_report.id)
            )
        )
        reuse_refs = list(
            session.exec(
                select(FinalReportReuseRef).where(FinalReportReuseRef.final_report_id == stored_report.id)
            )
        )
        stored_draft = session.get(Draft, draft_id)

    assert stored_report is not None
    assert payload["name"] == "Quarterly Review Final"
    assert payload["output_format"] == "markdown"
    assert payload["asset_ref_count"] == len(asset_refs)
    assert payload["reuse_ref_count"] == len(reuse_refs)
    assert payload["asset_ref_count"] >= 1
    assert payload["reuse_ref_count"] >= 1
    assert Path(stored_report.output_path).exists()
    assert stored_draft.status == DraftStatus.ARCHIVED


def test_archive_finalize_rejects_duplicate_archive_for_same_draft() -> None:
    settings = _settings("archive-duplicate")
    archive_service = ArchiveService()

    with session_scope(settings) as session:
        project_id, draft_id = _prepare_ready_draft(session)
        archive_service.finalize_report(
            session,
            settings,
            project_id=project_id,
            draft_id=draft_id,
            name="Quarterly Review Final",
        )

        with pytest.raises(ValidationError, match="already been archived"):
            archive_service.finalize_report(
                session,
                settings,
                project_id=project_id,
                draft_id=draft_id,
                name="Quarterly Review Final Again",
            )


def test_archive_finalize_requires_ready_draft() -> None:
    settings = _settings("archive-requires-ready")
    archive_service = ArchiveService()
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        asset_service = AssetService()
        collection_service = CollectionService()
        project_id = _create_project(session)
        for source_category, filename in [
            ("raw", "workflow-raw-01.md"),
            ("template", "workflow-template-01.md"),
            ("reference", "workflow-reference-01.txt"),
        ]:
            asset_service.add_asset(
                session,
                project_id=project_id,
                path=str(Path("samples/assets", filename).resolve()),
                source_category=source_category,
            )
        collection = collection_service.build_collection(
            session,
            project_id=project_id,
            name="Q2 Inputs",
            purpose="Review candidate inputs",
        )
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id, collection_id=collection["id"])

        with pytest.raises(ValidationError, match="must be ready"):
            archive_service.finalize_report(
                session,
                settings,
                project_id=project_id,
                draft_id=created["id"],
                name="Quarterly Review Final",
            )


def test_archive_finalize_rejects_drafts_without_traceable_sources() -> None:
    settings = _settings("archive-missing-sources")
    archive_service = ArchiveService()

    with session_scope(settings) as session:
        project_id, draft_id = _prepare_ready_draft(session)
        draft = session.get(Draft, draft_id)
        content_model = deepcopy(draft.content_model)
        for section in content_model["sections"]:
            for block in section["blocks"]:
                block["source_refs"] = {"asset_ids": [], "reuse_candidate_ids": []}
        draft.content_model = content_model
        session.add(draft)
        session.exec(delete(DraftAssetRef).where(DraftAssetRef.draft_id == draft_id))
        session.exec(delete(DraftReuseRef).where(DraftReuseRef.draft_id == draft_id))
        session.commit()

        with pytest.raises(ValidationError, match="no traceable source references"):
            archive_service.finalize_report(
                session,
                settings,
                project_id=project_id,
                draft_id=draft_id,
                name="Quarterly Review Final",
            )
