from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import select

from draftcore.app.config.settings import load_settings
from draftcore.app.db import session_scope
from draftcore.app.models import ReuseCandidate
from draftcore.app.services import AssetService, CollectionService, ProjectService, ReuseService
from draftcore.app.services.errors import ValidationError


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".pytest-tmp" / f"{name}-{uuid4().hex}.db").resolve()


def _settings(name: str):
    return load_settings(db_path_override=str(_db_path(name)))


def _create_project(session, *, name: str = "Task 3", topic: str = "Task 3 topic") -> int:
    project = ProjectService().create_project(
        session,
        name=name,
        topic=topic,
        target_output="markdown",
        default_status="active",
    )
    assert project.id is not None
    return project.id


def _add_asset(
    session,
    *,
    asset_service: AssetService,
    project_id: int,
    filename: str,
    source_category: str,
    usage_note: str | None = None,
) -> None:
    asset_service.add_asset(
        session,
        project_id=project_id,
        path=str(Path("samples/assets", filename).resolve()),
        source_category=source_category,
        usage_note=usage_note,
    )


def _build_collection(
    session,
    *,
    collection_service: CollectionService,
    project_id: int,
    name: str,
) -> int:
    payload = collection_service.build_collection(
        session,
        project_id=project_id,
        name=name,
        purpose=f"{name} purpose",
    )
    return payload["id"]


def test_find_reuse_resolves_single_collection_and_returns_traceable_candidates() -> None:
    settings = _settings("reuse-single-collection")
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id = _create_project(session)
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-template-01.md",
            source_category="template",
            usage_note="q2 reusable structure",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-reference-01.txt",
            source_category="reference",
            usage_note="q2 historical evidence",
        )
        collection_id = _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Q2 Inputs",
        )

        payload = reuse_service.find_reuse(session, project_id=project_id)
        stored = list(session.exec(select(ReuseCandidate).where(ReuseCandidate.project_id == project_id)))

    assert payload["collection_id"] == collection_id
    assert payload["candidate_count"] == 2
    assert payload["template_candidate_count"] == 1
    assert payload["reference_candidate_count"] == 1
    assert payload["degraded_count"] == 0
    assert [item["candidate_type"] for item in payload["items"]] == ["structure", "paragraph"]
    assert payload["items"][0]["path"].endswith("workflow-template-01.md")
    assert payload["items"][1]["path"].endswith("workflow-reference-01.txt")
    assert len(stored) == 2


def test_find_reuse_requires_explicit_collection_when_multiple_collections_exist() -> None:
    settings = _settings("reuse-multi-collection")
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Multiple collections", topic="Explicit selection")
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-template-01.md",
            source_category="template",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-reference-01.txt",
            source_category="reference",
        )
        _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Inputs A",
        )
        _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Inputs B",
        )

        with pytest.raises(ValidationError, match="multiple collections"):
            reuse_service.find_reuse(session, project_id=project_id)


def test_find_reuse_refreshes_project_candidates_instead_of_accumulating() -> None:
    settings = _settings("reuse-refresh")
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Refresh", topic="Reuse refresh")
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-template-01.md",
            source_category="template",
            usage_note="q2 reusable structure",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-reference-01.txt",
            source_category="reference",
            usage_note="q2 historical evidence",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-image-01.png",
            source_category="template",
        )
        _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Main Inputs",
        )

        first_payload = reuse_service.find_reuse(session, project_id=project_id, limit=3)
        second_payload = reuse_service.find_reuse(session, project_id=project_id, keywords="q2", limit=2)
        stored = list(session.exec(select(ReuseCandidate).where(ReuseCandidate.project_id == project_id)))

    assert first_payload["candidate_count"] == 3
    assert first_payload["degraded_count"] == 1
    assert second_payload["candidate_count"] == 2
    assert second_payload["degraded_count"] == 0
    assert len(stored) == 2


def test_find_reuse_fails_when_only_path_level_candidates_are_available() -> None:
    settings = _settings("reuse-path-only")
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Path only", topic="Degraded reuse")
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-image-01.png",
            source_category="template",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="parser-docx-partial-01.docx",
            source_category="reference",
        )
        _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Fallback Inputs",
        )

        with pytest.raises(ValidationError, match="Only path-level references"):
            reuse_service.find_reuse(session, project_id=project_id)


def test_find_reuse_keywords_filter_narrows_results_and_keeps_sources_traceable() -> None:
    settings = _settings("reuse-keywords")
    asset_service = AssetService()
    collection_service = CollectionService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Keyword filter", topic="Traceable filtering")
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-template-01.md",
            source_category="template",
            usage_note="q2 reusable structure",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-reference-01.txt",
            source_category="reference",
            usage_note="q2 historical evidence",
        )
        _add_asset(
            session,
            asset_service=asset_service,
            project_id=project_id,
            filename="workflow-image-01.png",
            source_category="template",
        )
        _build_collection(
            session,
            collection_service=collection_service,
            project_id=project_id,
            name="Keyword Inputs",
        )

        payload = reuse_service.find_reuse(session, project_id=project_id, keywords="Q2")

    assert payload["candidate_count"] == 2
    assert payload["degraded_count"] == 0
    assert payload["keywords"] == "Q2"
    assert {item["source_category"] for item in payload["items"]} == {"template", "reference"}
    assert all(item["path"] for item in payload["items"])

