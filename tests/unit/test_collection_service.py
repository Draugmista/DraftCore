from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import select

from draftcore.app.config.settings import load_settings
from draftcore.app.db import session_scope
from draftcore.app.models import Asset, AssetCollectionItem, ProjectAsset
from draftcore.app.models.enums import FileType, IngestionStatus, SourceCategory
from draftcore.app.services import AssetService, CollectionService, ProjectService
from draftcore.app.services.collection_service import (
    derive_collection_candidate_flag,
    derive_collection_usage_note,
)
from draftcore.app.services.errors import ValidationError


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".pytest-tmp" / f"{name}-{uuid4().hex}.db").resolve()


def _settings(name: str):
    return load_settings(db_path_override=str(_db_path(name)))


def _create_project(session, *, name: str = "Task 2", topic: str = "Task 2 topic") -> int:
    project = ProjectService().create_project(
        session,
        name=name,
        topic=topic,
        target_output="markdown",
        default_status="active",
    )
    assert project.id is not None
    return project.id


def test_derive_collection_usage_note_prefers_project_relation_note() -> None:
    asset = Asset(
        name="asset.md",
        path="C:/assets/asset.md",
        file_type=FileType.MD,
        source_category=SourceCategory.RAW,
        usage_note="asset note",
        ingestion_status=IngestionStatus.PARSED,
    )
    project_asset = ProjectAsset(project_id=1, asset_id=1, relation_note="project note")

    assert derive_collection_usage_note(project_asset, asset) == "project note"


def test_derive_collection_usage_note_uses_source_category_default() -> None:
    asset = Asset(
        name="template.md",
        path="C:/assets/template.md",
        file_type=FileType.MD,
        source_category=SourceCategory.TEMPLATE,
        ingestion_status=IngestionStatus.PARSED,
    )
    project_asset = ProjectAsset(project_id=1, asset_id=1)

    assert derive_collection_usage_note(project_asset, asset) == "structure template"


def test_derive_collection_candidate_flag_rules() -> None:
    raw_asset = Asset(
        name="raw.md",
        path="C:/assets/raw.md",
        file_type=FileType.MD,
        source_category=SourceCategory.RAW,
        ingestion_status=IngestionStatus.PARSED,
    )
    raw_link = ProjectAsset(project_id=1, asset_id=1)
    noted_raw_link = ProjectAsset(project_id=1, asset_id=1, relation_note="background reference")
    template_asset = Asset(
        name="template.md",
        path="C:/assets/template.md",
        file_type=FileType.MD,
        source_category=SourceCategory.TEMPLATE,
        ingestion_status=IngestionStatus.PARSED,
    )
    reference_asset = Asset(
        name="reference.md",
        path="C:/assets/reference.md",
        file_type=FileType.MD,
        source_category=SourceCategory.REFERENCE,
        ingestion_status=IngestionStatus.PARSED,
    )

    assert derive_collection_candidate_flag(raw_link, raw_asset) is False
    assert derive_collection_candidate_flag(noted_raw_link, raw_asset) is True
    assert derive_collection_candidate_flag(ProjectAsset(project_id=1, asset_id=2), template_asset) is True
    assert derive_collection_candidate_flag(ProjectAsset(project_id=1, asset_id=3), reference_asset) is True


def test_build_collection_refreshes_same_name_without_duplicate_items() -> None:
    settings = _settings("refresh-collection")
    asset_service = AssetService()
    collection_service = CollectionService()

    with session_scope(settings) as session:
        project_id = _create_project(session)
        asset_service.add_asset(
            session,
            project_id=project_id,
            path=str(Path("samples/assets/workflow-raw-01.md").resolve()),
            source_category="raw",
        )
        asset_service.add_asset(
            session,
            project_id=project_id,
            path=str(Path("samples/assets/workflow-template-01.md").resolve()),
            source_category="template",
        )

        first_payload = collection_service.build_collection(
            session,
            project_id=project_id,
            name="Main Inputs",
            purpose="Initial build",
        )
        collection_id = first_payload["id"]

        asset_service.add_asset(
            session,
            project_id=project_id,
            path=str(Path("samples/assets/workflow-reference-01.txt").resolve()),
            source_category="reference",
        )

        second_payload = collection_service.build_collection(
            session,
            project_id=project_id,
            name="Main Inputs",
            purpose="Refreshed build",
        )
        items = list(
            session.exec(
                select(AssetCollectionItem).where(AssetCollectionItem.collection_id == collection_id)
            )
        )

    assert first_payload["created"] is True
    assert second_payload["created"] is False
    assert second_payload["id"] == collection_id
    assert second_payload["purpose"] == "Refreshed build"
    assert second_payload["asset_count"] == 3
    assert len(items) == 3


def test_build_collection_rejects_empty_project() -> None:
    settings = _settings("empty-project")
    collection_service = CollectionService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Empty", topic="No assets yet")
        with pytest.raises(ValidationError):
            collection_service.build_collection(
                session,
                project_id=project_id,
                name="Main Inputs",
                purpose="Should fail",
            )


def test_build_collection_includes_failed_assets() -> None:
    settings = _settings("failed-asset")
    asset_service = AssetService()
    collection_service = CollectionService()

    with session_scope(settings) as session:
        project_id = _create_project(session, name="Failed asset", topic="Degraded collection")
        asset_service.add_asset(
            session,
            project_id=project_id,
            path=str(Path("samples/assets/parser-docx-partial-01.docx").resolve()),
            source_category="reference",
        )

        payload = collection_service.build_collection(
            session,
            project_id=project_id,
            name="Fallback Inputs",
            purpose="Keep degraded assets visible",
        )

    assert payload["asset_count"] == 1
    assert payload["candidate_count"] == 1
    assert payload["usage_note_coverage"]["ratio"] == 1.0
    assert payload["items"][0]["usage_note"] == "history reference"
    assert payload["items"][0]["ingestion_status"] == "failed"
