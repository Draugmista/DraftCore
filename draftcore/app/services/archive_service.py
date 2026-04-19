from __future__ import annotations

from pathlib import Path

from sqlmodel import select

from draftcore.app.config.settings import AppSettings
from draftcore.app.models import (
    Asset,
    Draft,
    DraftAssetRef,
    DraftReuseRef,
    FinalReport,
    FinalReportAssetRef,
    FinalReportReuseRef,
    ReuseCandidate,
)
from draftcore.app.models.entities import utc_now
from draftcore.app.models.enums import DraftStatus, OutputFormat
from draftcore.app.services.errors import NotFoundError, ValidationError
from draftcore.app.services.export_service import ExportService


class ArchiveService:
    def __init__(self) -> None:
        self.export_service = ExportService()

    def finalize_report(
        self,
        session,
        settings: AppSettings,
        *,
        project_id: int,
        draft_id: int,
        name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        draft = session.get(Draft, draft_id)
        if draft is None:
            raise NotFoundError(f"Draft {draft_id} does not exist.")
        if draft.project_id != project_id:
            raise ValidationError(f"Draft {draft_id} does not belong to project {project_id}.")
        existing_report = session.exec(select(FinalReport).where(FinalReport.draft_id == draft_id)).first()
        if existing_report is not None:
            raise ValidationError(f"Draft {draft_id} has already been archived as final report {existing_report.id}.")
        if draft.status != DraftStatus.READY:
            raise ValidationError(f"Draft {draft_id} must be ready before archive finalize.")

        report_name = name.strip()
        if not report_name:
            raise ValidationError("Archived report name cannot be empty.")

        asset_ids, reuse_candidate_ids = self._collect_source_ids(session, draft)
        if not asset_ids and not reuse_candidate_ids:
            raise ValidationError(
                f"Draft {draft_id} has no traceable source references and cannot be archived."
            )

        rendered_output_path: Path | None = None
        archived_at = utc_now()
        try:
            render_payload = self.export_service.render_draft(
                session,
                settings,
                draft_id=draft_id,
                output_format=OutputFormat.MARKDOWN.value,
                output_path=output_path,
                title_override=report_name,
            )
            rendered_output_path = render_payload["output_path"]

            final_report = FinalReport(
                project_id=project_id,
                draft_id=draft_id,
                name=report_name,
                output_format=OutputFormat.MARKDOWN.value,
                output_path=rendered_output_path.as_posix(),
                archived_at=archived_at,
            )
            session.add(final_report)
            session.flush()

            for asset in self._load_assets(session, asset_ids):
                session.add(
                    FinalReportAssetRef(
                        final_report_id=final_report.id,
                        asset_id=asset.id,
                        ref_role=asset.source_category.value,
                    )
                )

            for candidate_id in reuse_candidate_ids:
                session.add(
                    FinalReportReuseRef(
                        final_report_id=final_report.id,
                        reuse_candidate_id=candidate_id,
                    )
                )

            draft.status = DraftStatus.ARCHIVED
            draft.updated_at = archived_at
            session.add(draft)
            session.commit()
            return self.get_report_detail(session, final_report.id)
        except Exception:
            session.rollback()
            if rendered_output_path is not None:
                self._cleanup_file(rendered_output_path)
            raise

    def get_report_detail(self, session, report_id: int) -> dict[str, object]:
        report = session.get(FinalReport, report_id)
        if report is None:
            raise NotFoundError(f"Final report {report_id} does not exist.")

        asset_refs = list(
            session.exec(
                select(FinalReportAssetRef, Asset)
                .join(Asset, onclause=FinalReportAssetRef.asset_id == Asset.id)
                .where(FinalReportAssetRef.final_report_id == report_id)
                .order_by(Asset.id.asc())
            ).all()
        )
        reuse_refs = list(
            session.exec(
                select(FinalReportReuseRef, ReuseCandidate, Asset)
                .join(ReuseCandidate, onclause=FinalReportReuseRef.reuse_candidate_id == ReuseCandidate.id)
                .join(Asset, onclause=ReuseCandidate.asset_id == Asset.id)
                .where(FinalReportReuseRef.final_report_id == report_id)
                .order_by(ReuseCandidate.id.asc())
            ).all()
        )

        return {
            "id": report.id,
            "project_id": report.project_id,
            "draft_id": report.draft_id,
            "name": report.name,
            "output_format": report.output_format,
            "output_path": Path(report.output_path),
            "archived_at": report.archived_at,
            "asset_ref_count": len(asset_refs),
            "reuse_ref_count": len(reuse_refs),
            "asset_refs": [
                {
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "source_category": asset.source_category,
                    "ref_role": ref.ref_role,
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
        }

    def get_latest_project_report_detail(self, session, project_id: int) -> dict[str, object]:
        report = session.exec(
            select(FinalReport)
            .where(FinalReport.project_id == project_id)
            .order_by(FinalReport.archived_at.desc(), FinalReport.id.desc())
        ).first()
        if report is None:
            raise NotFoundError(f"Project {project_id} has no archived final report yet.")
        return self.get_report_detail(session, report.id)

    def get_project_final_report_status(self, session, project_id: int) -> str:
        report = session.exec(
            select(FinalReport.id).where(FinalReport.project_id == project_id).limit(1)
        ).first()
        return "archived" if report is not None else "not_archived"

    def _collect_source_ids(self, session, draft: Draft) -> tuple[list[int], list[int]]:
        asset_ids: list[int] = []
        reuse_candidate_ids: list[int] = []

        content_model = draft.content_model if isinstance(draft.content_model, dict) else {}
        sections = content_model.get("sections", [])
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue
                blocks = section.get("blocks", [])
                if not isinstance(blocks, list):
                    continue
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    source_refs = block.get("source_refs", {})
                    if not isinstance(source_refs, dict):
                        continue
                    asset_ids = self._merge_ids(asset_ids, source_refs.get("asset_ids"))
                    reuse_candidate_ids = self._merge_ids(
                        reuse_candidate_ids,
                        source_refs.get("reuse_candidate_ids"),
                    )

        if asset_ids or reuse_candidate_ids:
            return asset_ids, reuse_candidate_ids

        fallback_asset_ids = session.exec(
            select(DraftAssetRef.asset_id)
            .where(DraftAssetRef.draft_id == draft.id)
            .order_by(DraftAssetRef.asset_id.asc())
        ).all()
        fallback_reuse_ids = session.exec(
            select(DraftReuseRef.reuse_candidate_id)
            .where(DraftReuseRef.draft_id == draft.id)
            .order_by(DraftReuseRef.reuse_candidate_id.asc())
        ).all()
        return list(fallback_asset_ids), list(fallback_reuse_ids)

    def _load_assets(self, session, asset_ids: list[int]) -> list[Asset]:
        if not asset_ids:
            return []
        assets = list(session.exec(select(Asset).where(Asset.id.in_(asset_ids))).all())
        by_id = {asset.id: asset for asset in assets}
        return [by_id[asset_id] for asset_id in asset_ids if asset_id in by_id]

    def _merge_ids(self, merged_ids: list[int], candidate_ids: object) -> list[int]:
        for candidate_id in candidate_ids if isinstance(candidate_ids, list) else []:
            if isinstance(candidate_id, int) and candidate_id not in merged_ids:
                merged_ids.append(candidate_id)
        return merged_ids

    def _cleanup_file(self, output_path: Path) -> None:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass
