from __future__ import annotations

import re

from sqlmodel import select

from draftcore.app.models import (
    Asset,
    AssetCollection,
    AssetCollectionItem,
    AssetContentProfile,
    Draft,
    DraftAssetRef,
    DraftReuseRef,
    ReuseCandidate,
    ReportProject,
)
from draftcore.app.models.entities import utc_now
from draftcore.app.models.enums import DraftStatus, ReuseCandidateType
from draftcore.app.services.errors import NotFoundError, ValidationError


FALLBACK_HEADINGS = [
    "背景与目标",
    "支撑事实",
    "待补充事项",
]


class DraftService:
    def create_draft(
        self,
        session,
        *,
        project_id: int,
        collection_id: int | None = None,
        title: str | None = None,
    ) -> dict[str, object]:
        project = self._get_project(session, project_id)
        self._ensure_project_has_no_draft(session, project_id)
        collection = self._resolve_collection(session, project_id=project_id, collection_id=collection_id)
        assets = self._load_collection_assets(session, collection.id)
        if not assets:
            raise ValidationError(
                f"Collection {collection.id} has no assets and cannot seed a draft."
            )

        template_candidate, reference_candidate = self._load_reuse_inputs(session, project_id=project_id)
        draft_name = title.strip() if title and title.strip() else f"{project.name} Draft"
        content_model, source_snapshot = self._build_content_model(
            draft_name=draft_name,
            project=project,
            collection=collection,
            assets=assets,
            template_candidate=template_candidate,
            reference_candidate=reference_candidate,
        )

        draft = Draft(
            project_id=project_id,
            name=draft_name,
            version_label="v1",
            status=DraftStatus.DRAFT,
            content_model=content_model,
            source_snapshot=source_snapshot,
        )
        session.add(draft)
        session.flush()

        for _, asset, _ in assets:
            session.add(
                DraftAssetRef(
                    draft_id=draft.id,
                    asset_id=asset.id,
                    ref_type="context",
                )
            )

        for candidate in [template_candidate, reference_candidate]:
            session.add(
                DraftReuseRef(
                    draft_id=draft.id,
                    reuse_candidate_id=candidate.id,
                )
            )

        session.commit()
        return self.get_draft_detail(session, draft.id)

    def get_draft_detail(self, session, draft_id: int) -> dict[str, object]:
        draft = session.get(Draft, draft_id)
        if draft is None:
            raise NotFoundError(f"Draft {draft_id} does not exist.")

        asset_refs = list(
            session.exec(
                select(DraftAssetRef, Asset)
                .join(Asset, onclause=DraftAssetRef.asset_id == Asset.id)
                .where(DraftAssetRef.draft_id == draft_id)
                .order_by(Asset.created_at.asc(), Asset.id.asc())
            ).all()
        )
        reuse_refs = list(
            session.exec(
                select(DraftReuseRef, ReuseCandidate, Asset)
                .join(ReuseCandidate, onclause=DraftReuseRef.reuse_candidate_id == ReuseCandidate.id)
                .join(Asset, onclause=ReuseCandidate.asset_id == Asset.id)
                .where(DraftReuseRef.draft_id == draft_id)
                .order_by(ReuseCandidate.score_hint.desc(), ReuseCandidate.id.asc())
            ).all()
        )

        content_model = draft.content_model
        sections = list(content_model.get("sections", [])) if isinstance(content_model, dict) else []
        generation_mode = content_model.get("generation_mode") if isinstance(content_model, dict) else None

        return {
            "id": draft.id,
            "project_id": draft.project_id,
            "name": draft.name,
            "version_label": draft.version_label,
            "status": draft.status,
            "generation_mode": generation_mode,
            "section_count": len(sections),
            "content_model": content_model,
            "source_snapshot": draft.source_snapshot,
            "asset_ref_count": len(asset_refs),
            "reuse_ref_count": len(reuse_refs),
            "asset_refs": [
                {
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "source_category": asset.source_category,
                    "ref_type": ref.ref_type,
                }
                for ref, asset in asset_refs
            ],
            "reuse_refs": [
                {
                    "reuse_candidate_id": candidate.id,
                    "asset_id": candidate.asset_id,
                    "asset_name": asset.name,
                    "source_category": asset.source_category,
                    "candidate_type": candidate.candidate_type,
                }
                for ref, candidate, asset in reuse_refs
            ],
            "created_at": draft.created_at,
            "updated_at": draft.updated_at,
        }

    def get_project_draft_status(self, session, project_id: int) -> str:
        draft = session.exec(select(Draft).where(Draft.project_id == project_id)).first()
        if draft is None:
            return "not_started"
        return draft.status.value

    def _get_project(self, session, project_id: int) -> ReportProject:
        project = session.get(ReportProject, project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} does not exist.")
        return project

    def _ensure_project_has_no_draft(self, session, project_id: int) -> None:
        existing = session.exec(select(Draft).where(Draft.project_id == project_id)).first()
        if existing is not None:
            raise ValidationError(
                f"Project {project_id} already has draft {existing.id}. Use draft update in task 5 instead."
            )

    def _resolve_collection(
        self,
        session,
        *,
        project_id: int,
        collection_id: int | None,
    ) -> AssetCollection:
        if collection_id is not None:
            collection = session.get(AssetCollection, collection_id)
            if collection is None:
                raise ValidationError(f"Collection {collection_id} does not exist.")
            if collection.project_id != project_id:
                raise ValidationError(
                    f"Collection {collection_id} does not belong to project {project_id}."
                )
            return collection

        collections = list(
            session.exec(
                select(AssetCollection)
                .where(AssetCollection.project_id == project_id)
                .order_by(AssetCollection.created_at.desc(), AssetCollection.id.desc())
            )
        )
        if not collections:
            raise ValidationError(
                f"Project {project_id} has no asset collections yet. Build a collection before draft create."
            )
        if len(collections) > 1:
            raise ValidationError(
                f"Project {project_id} has multiple collections; please provide --collection-id."
            )
        return collections[0]

    def _load_collection_assets(
        self,
        session,
        collection_id: int,
    ) -> list[tuple[AssetCollectionItem, Asset, AssetContentProfile | None]]:
        statement = (
            select(AssetCollectionItem, Asset, AssetContentProfile)
            .join(Asset, onclause=AssetCollectionItem.asset_id == Asset.id)
            .outerjoin(AssetContentProfile, onclause=AssetContentProfile.asset_id == Asset.id)
            .where(AssetCollectionItem.collection_id == collection_id)
            .order_by(Asset.created_at.asc(), Asset.id.asc())
        )
        return list(session.exec(statement).all())

    def _load_reuse_inputs(
        self,
        session,
        *,
        project_id: int,
    ) -> tuple[ReuseCandidate, ReuseCandidate]:
        candidates = list(
            session.exec(
                select(ReuseCandidate)
                .where(ReuseCandidate.project_id == project_id)
                .order_by(ReuseCandidate.score_hint.desc(), ReuseCandidate.id.asc())
            )
        )
        if not candidates:
            raise ValidationError(
                f"Project {project_id} has no reuse candidates yet. Run reuse find before draft create."
            )

        template_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate.candidate_type in {ReuseCandidateType.STRUCTURE, ReuseCandidateType.SECTION}
            ),
            None,
        )
        if template_candidate is None:
            raise ValidationError(
                f"Project {project_id} has no template-style reuse result available for draft generation."
            )

        reference_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate.candidate_type in {ReuseCandidateType.PARAGRAPH, ReuseCandidateType.EXPRESSION}
            ),
            None,
        )
        if reference_candidate is None:
            raise ValidationError(
                f"Project {project_id} has no reference-style reuse result available for draft generation."
            )

        return template_candidate, reference_candidate

    def _build_content_model(
        self,
        *,
        draft_name: str,
        project: ReportProject,
        collection: AssetCollection,
        assets: list[tuple[AssetCollectionItem, Asset, AssetContentProfile | None]],
        template_candidate: ReuseCandidate,
        reference_candidate: ReuseCandidate,
    ) -> tuple[dict[str, object], dict[str, object]]:
        headings = self._extract_headings(template_candidate.snippet)
        generation_mode = "template"
        if len(headings) < 2:
            headings = list(FALLBACK_HEADINGS)
            generation_mode = "manual-fallback"
        else:
            for fallback in FALLBACK_HEADINGS:
                if len(headings) >= 3:
                    break
                if fallback not in headings:
                    headings.append(fallback)
            headings = headings[:3]

        raw_context = self._build_asset_context_text(assets)
        sections = [
            {
                "heading": headings[0],
                "blocks": [
                    {
                        "type": "text",
                        "text": (
                            f"本草稿围绕“{project.topic}”建立，当前基于模板结构和已确认素材形成起草入口。"
                        ),
                        "source_refs": {
                            "asset_ids": [template_candidate.asset_id],
                            "reuse_candidate_ids": [template_candidate.id],
                        },
                    }
                ],
            },
            {
                "heading": headings[1],
                "blocks": [
                    {
                        "type": "text",
                        "text": reference_candidate.snippet.strip(),
                        "source_refs": {
                            "asset_ids": [reference_candidate.asset_id],
                            "reuse_candidate_ids": [reference_candidate.id],
                        },
                    }
                ],
            },
            {
                "heading": headings[2],
                "blocks": [
                    {
                        "type": "text",
                        "text": raw_context,
                        "source_refs": {
                            "asset_ids": [asset.id for _, asset, _ in assets],
                            "reuse_candidate_ids": [],
                        },
                    }
                ],
            },
        ]

        asset_ids = [asset.id for _, asset, _ in assets]
        reuse_candidate_ids = [template_candidate.id, reference_candidate.id]
        snapshot = {
            "project_id": project.id,
            "collection_id": collection.id,
            "asset_ids": asset_ids,
            "reuse_candidate_ids": reuse_candidate_ids,
            "generation_mode": generation_mode,
            "generated_at": utc_now().isoformat(),
        }
        content_model = {
            "title": draft_name,
            "generation_mode": generation_mode,
            "sections": sections,
        }
        return content_model, snapshot

    def _extract_headings(self, snippet: str) -> list[str]:
        lines = [line.strip() for line in snippet.splitlines() if line.strip()]
        markdown_headings = [
            re.sub(r"^#+\s*", "", line).strip()
            for line in lines
            if line.startswith("#")
        ]
        if markdown_headings:
            return [heading for heading in markdown_headings if heading]

        return [
            line
            for line in lines
            if len(line) <= 60 and not line.endswith(".")
        ]

    def _build_asset_context_text(
        self,
        assets: list[tuple[AssetCollectionItem, Asset, AssetContentProfile | None]],
    ) -> str:
        lines: list[str] = []
        for item, asset, profile in assets:
            summary = None
            if profile is not None:
                summary = profile.summary or profile.title or profile.structure_excerpt
            detail = summary or item.usage_note or asset.usage_note or asset.name
            lines.append(f"- {asset.name}: {detail}")

        lines.append("- 请在任务 5 中继续补充细节、统一表达，并确认哪些素材进入最终报告。")
        return "\n".join(lines)
