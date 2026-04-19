from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import select

from draftcore.app.config.settings import load_settings
from draftcore.app.db import session_scope
from draftcore.app.models import Asset, Draft, DraftAssetRef, DraftReuseRef, ReuseCandidate
from draftcore.app.models.enums import DraftStatus, ReuseCandidateType, SourceCategory
from draftcore.app.services import AssetService, CollectionService, DraftService, ProjectService, ReuseService
from draftcore.app.services.errors import NotFoundError, ValidationError


def _db_path(name: str) -> Path:
    return (Path.cwd() / ".pytest-tmp" / f"{name}-{uuid4().hex}.db").resolve()


def _settings(name: str):
    return load_settings(db_path_override=str(_db_path(name)))


def _create_project(session, *, name: str = "Task 4", topic: str = "Task 4 topic") -> int:
    project = ProjectService().create_project(
        session,
        name=name,
        topic=topic,
        target_output="markdown",
        default_status="active",
    )
    assert project.id is not None
    return project.id


def _prepare_collection(session) -> tuple[int, int]:
    asset_service = AssetService()
    collection_service = CollectionService()
    project_id = _create_project(session, name="Quarterly Review", topic="Q2 performance")
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
    payload = collection_service.build_collection(
        session,
        project_id=project_id,
        name="Q2 Inputs",
        purpose="Review candidate inputs",
    )
    return project_id, payload["id"]


def _add_late_asset(session, project_id: int) -> int:
    asset = AssetService().add_asset(
        session,
        project_id=project_id,
        path=str(Path("samples/assets", "workflow-raw-02.md").resolve()),
        source_category="raw",
        usage_note="late evidence",
    )
    return asset["id"]


def test_create_draft_persists_traceable_main_draft() -> None:
    settings = _settings("draft-traceable")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, collection_id = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)

        payload = draft_service.create_draft(session, project_id=project_id, title="Q2 Main Draft")
        stored_draft = session.exec(select(Draft).where(Draft.project_id == project_id)).first()
        asset_refs = list(session.exec(select(DraftAssetRef).where(DraftAssetRef.draft_id == stored_draft.id)))
        reuse_refs = list(session.exec(select(DraftReuseRef).where(DraftReuseRef.draft_id == stored_draft.id)))

    assert payload["name"] == "Q2 Main Draft"
    assert payload["generation_mode"] == "template"
    assert payload["section_count"] == 3
    assert payload["asset_ref_count"] == 3
    assert payload["reuse_ref_count"] == 2
    assert payload["source_snapshot"]["collection_id"] == collection_id
    assert payload["source_snapshot"]["reuse_candidate_ids"] == [1, 2]
    assert len(asset_refs) == 3
    assert len(reuse_refs) == 2


def test_create_draft_uses_manual_fallback_when_template_has_no_headings() -> None:
    settings = _settings("draft-manual-fallback")
    draft_service = DraftService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        assets = list(session.exec(select(Asset).order_by(Asset.id.asc())))
        template_asset = next(asset for asset in assets if asset.source_category == SourceCategory.TEMPLATE)
        reference_asset = next(asset for asset in assets if asset.source_category == SourceCategory.REFERENCE)
        session.add(
            ReuseCandidate(
                project_id=project_id,
                asset_id=template_asset.id,
                candidate_type=ReuseCandidateType.SECTION,
                snippet="Use this structure to start the report.",
                reason="Template starter",
                score_hint=90,
            )
        )
        session.add(
            ReuseCandidate(
                project_id=project_id,
                asset_id=reference_asset.id,
                candidate_type=ReuseCandidateType.PARAGRAPH,
                snippet="Historical findings show a similar seasonal uplift in the previous year.",
                reason="Reference paragraph",
                score_hint=80,
            )
        )
        session.commit()

        payload = draft_service.create_draft(session, project_id=project_id)

    headings = [section["heading"] for section in payload["content_model"]["sections"]]
    assert payload["generation_mode"] == "manual-fallback"
    assert headings == ["背景与目标", "支撑事实", "待补充事项"]


def test_create_draft_rejects_duplicate_main_draft() -> None:
    settings = _settings("draft-duplicate")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        draft_service.create_draft(session, project_id=project_id)

        with pytest.raises(ValidationError, match="already has draft"):
            draft_service.create_draft(session, project_id=project_id)


def test_create_draft_requires_latest_reuse_candidates() -> None:
    settings = _settings("draft-missing-reuse")
    draft_service = DraftService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)

        with pytest.raises(ValidationError, match="Run reuse find"):
            draft_service.create_draft(session, project_id=project_id)


def test_update_draft_reuses_same_record_and_persists_revision_history() -> None:
    settings = _settings("draft-update-revision")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id)
        late_asset_id = _add_late_asset(session, project_id)

        payload = draft_service.update_draft(
            session,
            draft_id=created["id"],
            instructions="补充新增素材并统一表达",
            use_latest_assets=True,
        )
        detail = draft_service.get_draft_detail(session, created["id"])
        stored_draft = session.get(Draft, created["id"])

    assert payload["id"] == created["id"]
    assert payload["previous_version_label"] == "v1"
    assert payload["version_label"] == "v2"
    assert payload["status"] == "ready"
    assert payload["asset_ref_count"] == 4
    assert payload["assets_added_count"] == 1
    assert payload["revision_count"] == 1
    assert payload["updated_section_count"] == 1
    assert "supplement" in payload["change_summary"]
    assert stored_draft.status == DraftStatus.READY
    assert detail["revision_count"] == 1
    assert detail["last_revision"]["assets_added"] == [late_asset_id]
    assert detail["source_snapshot"]["asset_ids"][-1] == late_asset_id
    assert detail["content_model"]["sections"][-1]["blocks"][-1]["source_refs"]["asset_ids"] == [late_asset_id]


def test_update_draft_does_not_add_assets_without_flag() -> None:
    settings = _settings("draft-update-no-assets")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id)
        _add_late_asset(session, project_id)

        payload = draft_service.update_draft(
            session,
            draft_id=created["id"],
            instructions="整理已有内容",
            use_latest_assets=False,
        )

    assert payload["version_label"] == "v2"
    assert payload["asset_ref_count"] == 3
    assert payload["assets_added_count"] == 0


def test_update_draft_merges_section_blocks_and_unions_source_refs() -> None:
    settings = _settings("draft-update-merge")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id)
        stored_draft = session.get(Draft, created["id"])
        content_model = deepcopy(stored_draft.content_model)
        first_section = content_model["sections"][0]
        first_section["blocks"].append(
            {
                "type": "text",
                "text": "Additional context to merge.",
                "source_refs": {
                    "asset_ids": [2, 3],
                    "reuse_candidate_ids": [1, 2],
                },
            }
        )
        content_model["sections"][0] = first_section
        stored_draft.content_model = content_model
        session.add(stored_draft)
        session.commit()

        draft_service.update_draft(
            session,
            draft_id=created["id"],
            instructions="合并整理",
            use_latest_assets=False,
        )
        detail = draft_service.get_draft_detail(session, created["id"])

    merged_block = detail["content_model"]["sections"][0]["blocks"][0]
    assert len(detail["content_model"]["sections"][0]["blocks"]) == 1
    assert merged_block["source_refs"]["asset_ids"] == [2, 3]
    assert merged_block["source_refs"]["reuse_candidate_ids"] == [1, 2]


def test_update_draft_rejects_empty_instructions() -> None:
    settings = _settings("draft-update-empty")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id)

        with pytest.raises(ValidationError, match="cannot be empty"):
            draft_service.update_draft(session, draft_id=created["id"], instructions="   ")


def test_update_draft_rejects_missing_draft() -> None:
    settings = _settings("draft-update-missing")
    draft_service = DraftService()

    with session_scope(settings) as session:
        with pytest.raises(NotFoundError, match="Draft 999 does not exist"):
            draft_service.update_draft(session, draft_id=999, instructions="补充说明")


def test_update_draft_rejects_broken_content_model() -> None:
    settings = _settings("draft-update-broken")
    draft_service = DraftService()
    reuse_service = ReuseService()

    with session_scope(settings) as session:
        project_id, _ = _prepare_collection(session)
        reuse_service.find_reuse(session, project_id=project_id)
        created = draft_service.create_draft(session, project_id=project_id)
        stored_draft = session.get(Draft, created["id"])
        stored_draft.content_model = {"title": stored_draft.name, "sections": []}
        session.add(stored_draft)
        session.commit()

        with pytest.raises(ValidationError, match="no editable sections"):
            draft_service.update_draft(session, draft_id=created["id"], instructions="补充说明")
