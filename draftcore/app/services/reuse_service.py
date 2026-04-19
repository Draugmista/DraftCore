from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete
from sqlmodel import select

from draftcore.app.models import Asset, AssetCollection, AssetCollectionItem, AssetContentProfile, ReuseCandidate
from draftcore.app.models.entities import utc_now
from draftcore.app.models.enums import FileType, IngestionStatus, ReuseCandidateType, SourceCategory
from draftcore.app.services.errors import ValidationError
from draftcore.app.services.project_service import ProjectService


CONTENT_REUSE_FILE_TYPES = {
    FileType.MD,
    FileType.TXT,
    FileType.DOCX,
    FileType.PPTX,
}


@dataclass(slots=True)
class ReuseDraft:
    asset: Asset
    profile: AssetContentProfile | None
    collection_item: AssetCollectionItem
    candidate_type: ReuseCandidateType
    snippet: str
    reason: str
    score_hint: int


class ReuseService:
    def __init__(self) -> None:
        self.project_service = ProjectService()

    def find_reuse(
        self,
        session,
        *,
        project_id: int,
        collection_id: int | None = None,
        keywords: str | None = None,
        limit: int = 10,
    ) -> dict[str, object]:
        self.project_service.get_project(session, project_id)
        collection = self._resolve_collection(session, project_id=project_id, collection_id=collection_id)
        keyword_query = keywords.strip() if keywords else None
        candidates = self._build_candidates(
            session,
            collection_id=collection.id,
            keywords=keyword_query,
        )
        if not candidates:
            raise ValidationError(
                "No reusable template or reference assets matched the requested collection and filters."
            )

        limited_candidates = self._select_candidates(candidates, limit=limit)
        self._validate_selection(limited_candidates, limit=limit)

        session.exec(delete(ReuseCandidate).where(ReuseCandidate.project_id == project_id))
        session.flush()

        for draft in limited_candidates:
            session.add(
                ReuseCandidate(
                    project_id=project_id,
                    asset_id=draft.asset.id,
                    candidate_type=draft.candidate_type,
                    snippet=draft.snippet,
                    reason=draft.reason,
                    score_hint=draft.score_hint,
                )
            )

        session.commit()
        return self._build_payload(
            session,
            project_id=project_id,
            collection_id=collection.id,
            keywords=keyword_query,
            limit=limit,
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
                f"Project {project_id} has no asset collections yet. Build a collection before reuse find."
            )
        if len(collections) > 1:
            raise ValidationError(
                f"Project {project_id} has multiple collections; please provide --collection-id."
            )
        return collections[0]

    def _build_candidates(
        self,
        session,
        *,
        collection_id: int,
        keywords: str | None,
    ) -> list[ReuseDraft]:
        statement = (
            select(AssetCollectionItem, Asset, AssetContentProfile)
            .join(Asset, onclause=AssetCollectionItem.asset_id == Asset.id)
            .outerjoin(AssetContentProfile, onclause=AssetContentProfile.asset_id == Asset.id)
            .where(
                AssetCollectionItem.collection_id == collection_id,
                Asset.source_category.in_([SourceCategory.TEMPLATE, SourceCategory.REFERENCE]),
            )
            .order_by(Asset.created_at.asc(), Asset.id.asc())
        )
        rows = list(session.exec(statement).all())
        if not rows:
            raise ValidationError(
                "No template or reference assets are available in the selected collection."
            )

        candidates: list[ReuseDraft] = []
        for collection_item, asset, profile in rows:
            if keywords and not self._matches_keywords(
                asset=asset,
                profile=profile,
                usage_note=collection_item.usage_note,
                keywords=keywords,
            ):
                continue
            candidates.append(self._build_candidate(asset=asset, profile=profile, collection_item=collection_item))
        return candidates

    def _build_candidate(
        self,
        *,
        asset: Asset,
        profile: AssetContentProfile | None,
        collection_item: AssetCollectionItem,
    ) -> ReuseDraft:
        if asset.source_category == SourceCategory.TEMPLATE:
            return self._build_template_candidate(asset=asset, profile=profile, collection_item=collection_item)
        return self._build_reference_candidate(asset=asset, profile=profile, collection_item=collection_item)

    def _build_template_candidate(
        self,
        *,
        asset: Asset,
        profile: AssetContentProfile | None,
        collection_item: AssetCollectionItem,
    ) -> ReuseDraft:
        if self._supports_content_reuse(asset=asset, profile=profile):
            snippet = self._pick_template_snippet(profile)
            if snippet:
                candidate_type = (
                    ReuseCandidateType.STRUCTURE
                    if profile and profile.structure_excerpt and profile.structure_excerpt.strip()
                    else ReuseCandidateType.SECTION
                )
                return ReuseDraft(
                    asset=asset,
                    profile=profile,
                    collection_item=collection_item,
                    candidate_type=candidate_type,
                    snippet=snippet,
                    reason="Template structure can seed the draft outline for this project.",
                    score_hint=self._score(asset=asset, candidate_type=candidate_type, snippet=snippet),
                )

        return ReuseDraft(
            asset=asset,
            profile=profile,
            collection_item=collection_item,
            candidate_type=ReuseCandidateType.PATH_REFERENCE,
            snippet=asset.path,
            reason="Template asset is tracked as a path-level fallback because no reusable structure was extracted.",
            score_hint=self._score(asset=asset, candidate_type=ReuseCandidateType.PATH_REFERENCE, snippet=asset.path),
        )

    def _build_reference_candidate(
        self,
        *,
        asset: Asset,
        profile: AssetContentProfile | None,
        collection_item: AssetCollectionItem,
    ) -> ReuseDraft:
        if self._supports_content_reuse(asset=asset, profile=profile):
            paragraph = self._pick_reference_paragraph(profile)
            if paragraph:
                return ReuseDraft(
                    asset=asset,
                    profile=profile,
                    collection_item=collection_item,
                    candidate_type=ReuseCandidateType.PARAGRAPH,
                    snippet=paragraph,
                    reason="Historical content provides a reusable paragraph-level reference for the draft.",
                    score_hint=self._score(
                        asset=asset,
                        candidate_type=ReuseCandidateType.PARAGRAPH,
                        snippet=paragraph,
                    ),
                )
            snippet = self._pick_reference_expression(profile)
            if snippet:
                return ReuseDraft(
                    asset=asset,
                    profile=profile,
                    collection_item=collection_item,
                    candidate_type=ReuseCandidateType.EXPRESSION,
                    snippet=snippet,
                    reason="Historical wording provides a reusable expression reference for the draft.",
                    score_hint=self._score(
                        asset=asset,
                        candidate_type=ReuseCandidateType.EXPRESSION,
                        snippet=snippet,
                    ),
                )

        return ReuseDraft(
            asset=asset,
            profile=profile,
            collection_item=collection_item,
            candidate_type=ReuseCandidateType.PATH_REFERENCE,
            snippet=asset.path,
            reason="Reference asset is tracked as a path-level fallback because no reusable text was extracted.",
            score_hint=self._score(asset=asset, candidate_type=ReuseCandidateType.PATH_REFERENCE, snippet=asset.path),
        )

    def _supports_content_reuse(self, *, asset: Asset, profile: AssetContentProfile | None) -> bool:
        if asset.file_type not in CONTENT_REUSE_FILE_TYPES:
            return False
        if asset.ingestion_status not in {IngestionStatus.PARSED, IngestionStatus.PARTIAL}:
            return False
        if profile is None:
            return False
        return any(
            value and value.strip()
            for value in [
                profile.structure_excerpt,
                profile.searchable_text,
                profile.summary,
                profile.title,
            ]
        )

    def _pick_template_snippet(self, profile: AssetContentProfile | None) -> str | None:
        if profile is None:
            return None
        for value in [profile.structure_excerpt, profile.summary, profile.title]:
            if value and value.strip():
                return value.strip()
        return None

    def _pick_reference_paragraph(self, profile: AssetContentProfile | None) -> str | None:
        if profile is None or not profile.searchable_text:
            return None
        paragraphs = [line.strip() for line in profile.searchable_text.splitlines() if line.strip()]
        if not paragraphs:
            return None
        return paragraphs[0]

    def _pick_reference_expression(self, profile: AssetContentProfile | None) -> str | None:
        if profile is None:
            return None
        for value in [profile.summary, profile.title]:
            if value and value.strip():
                return value.strip()
        return None

    def _score(
        self,
        *,
        asset: Asset,
        candidate_type: ReuseCandidateType,
        snippet: str,
    ) -> int:
        base_by_category = {
            SourceCategory.TEMPLATE: 80,
            SourceCategory.REFERENCE: 70,
        }
        base_by_type = {
            ReuseCandidateType.STRUCTURE: 15,
            ReuseCandidateType.SECTION: 10,
            ReuseCandidateType.PARAGRAPH: 12,
            ReuseCandidateType.EXPRESSION: 8,
            ReuseCandidateType.PATH_REFERENCE: 1,
        }
        return base_by_category[asset.source_category] + base_by_type[candidate_type] + min(len(snippet) // 40, 9)

    def _matches_keywords(
        self,
        *,
        asset: Asset,
        profile: AssetContentProfile | None,
        usage_note: str,
        keywords: str,
    ) -> bool:
        haystack = "\n".join(
            value
            for value in [
                asset.name,
                usage_note,
                profile.title if profile else None,
                profile.summary if profile else None,
                profile.structure_excerpt if profile else None,
                profile.searchable_text if profile else None,
            ]
            if value
        ).lower()
        return keywords.lower() in haystack

    def _select_candidates(self, candidates: list[ReuseDraft], *, limit: int) -> list[ReuseDraft]:
        ordered = sorted(
            candidates,
            key=lambda item: (
                item.score_hint,
                item.asset.created_at,
                item.asset.id or 0,
            ),
            reverse=True,
        )
        if limit >= 2:
            template_candidate = next(
                (
                    item
                    for item in ordered
                    if item.asset.source_category == SourceCategory.TEMPLATE
                    and item.candidate_type != ReuseCandidateType.PATH_REFERENCE
                ),
                None,
            )
            reference_candidate = next(
                (
                    item
                    for item in ordered
                    if item.asset.source_category == SourceCategory.REFERENCE
                    and item.candidate_type != ReuseCandidateType.PATH_REFERENCE
                ),
                None,
            )
            selected: list[ReuseDraft] = []
            for item in [template_candidate, reference_candidate]:
                if item is not None:
                    selected.append(item)
            for item in ordered:
                if len(selected) >= limit:
                    break
                if item in selected:
                    continue
                selected.append(item)
            return selected[:limit]
        return ordered[:limit]

    def _validate_selection(self, candidates: list[ReuseDraft], *, limit: int) -> None:
        has_template_content = any(
            item.asset.source_category == SourceCategory.TEMPLATE
            and item.candidate_type != ReuseCandidateType.PATH_REFERENCE
            for item in candidates
        )
        has_reference_content = any(
            item.asset.source_category == SourceCategory.REFERENCE
            and item.candidate_type != ReuseCandidateType.PATH_REFERENCE
            for item in candidates
        )
        if has_template_content and has_reference_content:
            return

        if limit < 2:
            raise ValidationError(
                "The current --limit is too small to keep both template and reference reuse results."
            )
        if all(item.candidate_type == ReuseCandidateType.PATH_REFERENCE for item in candidates):
            raise ValidationError(
                "Only path-level references were produced; task 3 requires content-level or structure-level reuse results."
            )
        if not has_template_content:
            raise ValidationError("No content-level template reuse result could be produced for this project.")
        raise ValidationError("No content-level reference reuse result could be produced for this project.")

    def _build_payload(
        self,
        session,
        *,
        project_id: int,
        collection_id: int,
        keywords: str | None,
        limit: int,
    ) -> dict[str, object]:
        statement = (
            select(ReuseCandidate, Asset, AssetContentProfile)
            .join(Asset, onclause=ReuseCandidate.asset_id == Asset.id)
            .outerjoin(AssetContentProfile, onclause=AssetContentProfile.asset_id == Asset.id)
            .where(ReuseCandidate.project_id == project_id)
            .order_by(ReuseCandidate.score_hint.desc(), ReuseCandidate.id.asc())
        )
        rows = list(session.exec(statement).all())
        items = [
            self._serialize_candidate(candidate=candidate, asset=asset, profile=profile)
            for candidate, asset, profile in rows
        ]
        degraded_count = sum(
            1 for item in items if item["candidate_type"] == ReuseCandidateType.PATH_REFERENCE.value
        )
        template_count = sum(1 for item in items if item["source_category"] == SourceCategory.TEMPLATE.value)
        reference_count = sum(1 for item in items if item["source_category"] == SourceCategory.REFERENCE.value)
        return {
            "project_id": project_id,
            "collection_id": collection_id,
            "keywords": keywords,
            "limit": limit,
            "candidate_count": len(items),
            "template_candidate_count": template_count,
            "reference_candidate_count": reference_count,
            "degraded_count": degraded_count,
            "items": items,
            "generated_at": utc_now(),
        }

    def _serialize_candidate(
        self,
        *,
        candidate: ReuseCandidate,
        asset: Asset,
        profile: AssetContentProfile | None,
    ) -> dict[str, object]:
        return {
            "id": candidate.id,
            "asset_id": asset.id,
            "asset_name": asset.name,
            "source_category": asset.source_category,
            "candidate_type": candidate.candidate_type,
            "snippet": candidate.snippet,
            "reason": candidate.reason,
            "score_hint": candidate.score_hint,
            "path": asset.path,
            "title": profile.title if profile else None,
            "created_at": candidate.created_at,
        }
