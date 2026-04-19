from __future__ import annotations

import re
from pathlib import Path

from draftcore.app.config.settings import AppSettings
from draftcore.app.exporters import MarkdownExporter
from draftcore.app.models import Draft
from draftcore.app.models.enums import DraftStatus, OutputFormat
from draftcore.app.services.errors import NotFoundError, ValidationError


class ExportService:
    def __init__(self) -> None:
        self.markdown_exporter = MarkdownExporter()

    def render_draft(
        self,
        session,
        settings: AppSettings,
        *,
        draft_id: int,
        output_format: str,
        output_path: str | None = None,
        title_override: str | None = None,
    ) -> dict[str, object]:
        draft = session.get(Draft, draft_id)
        if draft is None:
            raise NotFoundError(f"Draft {draft_id} does not exist.")

        normalized_format = self._normalize_format(output_format)
        if draft.status not in {DraftStatus.READY, DraftStatus.ARCHIVED}:
            raise ValidationError(
                f"Draft {draft_id} must be ready or archived before export render."
            )

        resolved_output_path = self._resolve_output_path(
            settings,
            project_id=draft.project_id,
            draft_id=draft.id,
            draft_name=title_override or draft.name,
            output_path=output_path,
        )
        rendered = self.markdown_exporter.render(draft.content_model, title_override=title_override)
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(rendered, encoding="utf-8")

        return {
            "draft_id": draft.id,
            "project_id": draft.project_id,
            "format": normalized_format.value,
            "output_path": resolved_output_path,
        }

    def _normalize_format(self, output_format: str) -> OutputFormat:
        try:
            normalized_format = OutputFormat(output_format.strip().lower())
        except ValueError as exc:
            raise ValidationError(f"Unsupported export format: {output_format}") from exc
        if normalized_format is not OutputFormat.MARKDOWN:
            raise ValidationError("Only markdown export is supported in the current MVP.")
        return normalized_format

    def _resolve_output_path(
        self,
        settings: AppSettings,
        *,
        project_id: int,
        draft_id: int,
        draft_name: str,
        output_path: str | None,
    ) -> Path:
        if output_path and output_path.strip():
            return Path(output_path).expanduser().resolve()

        slug = self._slugify(draft_name)
        filename = f"{project_id}-{draft_id}-{slug}.md"
        return (settings.workspace.output_dir / filename).resolve()

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or "draft"
