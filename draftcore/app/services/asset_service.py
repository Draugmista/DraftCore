from __future__ import annotations

from pathlib import Path

from sqlmodel import select

from draftcore.app.models import Asset, AssetContentProfile, ProjectAsset
from draftcore.app.models.enums import FileType, IngestionStatus, SourceCategory
from draftcore.app.parsers import ParseResult, parse_asset
from draftcore.app.services.errors import NotFoundError, UnsupportedFeatureError, ValidationError
from draftcore.app.services.project_service import ProjectService


class AssetService:
    def __init__(self) -> None:
        self.project_service = ProjectService()

    def add_asset(
        self,
        session,
        *,
        project_id: int,
        path: str,
        source_category: str,
        usage_note: str | None = None,
    ) -> dict[str, object]:
        project = self.project_service.get_project(session, project_id)
        normalized_path = normalize_asset_path(path)
        category = parse_source_category(source_category)
        file_type = detect_file_type(normalized_path)

        asset = session.exec(select(Asset).where(Asset.path == normalized_path.as_posix())).first()
        created = False
        if asset is None:
            asset = Asset(
                name=normalized_path.name,
                path=normalized_path.as_posix(),
                file_type=file_type,
                source_category=category,
                topic_or_task=project.topic,
                usage_note=usage_note.strip() if usage_note else None,
                ingestion_status=IngestionStatus.PENDING,
            )
            session.add(asset)
            session.flush()
            created = True
        else:
            if asset.source_category != category:
                raise ValidationError(
                    "This asset is already registered with source_category "
                    f"{asset.source_category.value} and cannot switch to {category.value} in MVP v1."
                )
            asset.topic_or_task = asset.topic_or_task or project.topic
            if usage_note and not asset.usage_note:
                asset.usage_note = usage_note.strip()

        parse_result = _safe_parse(normalized_path, file_type)
        asset.ingestion_status = parse_result.status
        session.add(asset)
        session.flush()
        self._upsert_profile(session, asset.id, parse_result)
        self._link_asset_to_project(session, project_id=project_id, asset_id=asset.id, usage_note=usage_note)
        session.commit()

        detail = self.get_asset_detail(session, asset.id)
        detail["created"] = created
        detail["project_id"] = project_id
        return detail

    def list_project_assets(
        self,
        session,
        *,
        project_id: int,
        source_category: str | None = None,
        used_only: bool = False,
    ) -> dict[str, object]:
        self.project_service.get_project(session, project_id)
        if used_only:
            raise UnsupportedFeatureError(
                "The --used-only filter will be available after draft/archive references are implemented."
            )

        statement = (
            select(Asset)
            .join(ProjectAsset, onclause=ProjectAsset.asset_id == Asset.id)
            .where(ProjectAsset.project_id == project_id)
            .order_by(Asset.created_at.desc())
        )
        if source_category:
            statement = statement.where(Asset.source_category == parse_source_category(source_category))

        assets = list(session.exec(statement))
        return {
            "project_id": project_id,
            "asset_count": len(assets),
            "items": [self._serialize_asset_row(session, asset) for asset in assets],
        }

    def get_asset_detail(self, session, asset_id: int) -> dict[str, object]:
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise NotFoundError(f"Asset {asset_id} does not exist.")
        return self._serialize_asset_row(session, asset, include_profile=True, include_projects=True)

    def _serialize_asset_row(
        self,
        session,
        asset: Asset,
        *,
        include_profile: bool = False,
        include_projects: bool = False,
    ) -> dict[str, object]:
        row: dict[str, object] = {
            "id": asset.id,
            "name": asset.name,
            "path": asset.path,
            "file_type": asset.file_type,
            "source_category": asset.source_category,
            "topic_or_task": asset.topic_or_task,
            "usage_note": asset.usage_note,
            "ingestion_status": asset.ingestion_status,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
        }
        if include_profile:
            profile = session.get(AssetContentProfile, asset.id)
            row["profile"] = (
                {
                    "title": profile.title,
                    "summary": profile.summary,
                    "searchable_text": profile.searchable_text,
                    "structure_excerpt": profile.structure_excerpt,
                    "page_count": profile.page_count,
                    "paragraph_count": profile.paragraph_count,
                    "parser_name": profile.parser_name,
                    "extracted_at": profile.extracted_at,
                }
                if profile
                else None
            )
        if include_projects:
            links = list(session.exec(select(ProjectAsset).where(ProjectAsset.asset_id == asset.id)))
            row["projects"] = [{"project_id": link.project_id, "relation_note": link.relation_note} for link in links]
        return row

    def _upsert_profile(self, session, asset_id: int | None, parse_result) -> None:
        if asset_id is None:
            raise ValidationError("Asset ID must exist before writing a content profile.")
        profile = session.get(AssetContentProfile, asset_id)
        if profile is None:
            profile = AssetContentProfile(
                asset_id=asset_id,
                title=parse_result.title,
                summary=parse_result.summary,
                searchable_text=parse_result.searchable_text,
                structure_excerpt=parse_result.structure_excerpt,
                page_count=parse_result.page_count,
                paragraph_count=parse_result.paragraph_count,
                parser_name=parse_result.parser_name,
            )
        else:
            profile.title = parse_result.title
            profile.summary = parse_result.summary
            profile.searchable_text = parse_result.searchable_text
            profile.structure_excerpt = parse_result.structure_excerpt
            profile.page_count = parse_result.page_count
            profile.paragraph_count = parse_result.paragraph_count
            profile.parser_name = parse_result.parser_name
        session.add(profile)

    def _link_asset_to_project(
        self,
        session,
        *,
        project_id: int,
        asset_id: int | None,
        usage_note: str | None,
    ) -> None:
        if asset_id is None:
            raise ValidationError("Asset ID must exist before linking it to a project.")
        link = session.get(ProjectAsset, (project_id, asset_id))
        if link is None:
            link = ProjectAsset(
                project_id=project_id,
                asset_id=asset_id,
                relation_note=usage_note.strip() if usage_note else None,
            )
        elif usage_note:
            link.relation_note = usage_note.strip()
        session.add(link)


def normalize_asset_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise ValidationError(f"Asset path does not exist: {candidate}")
    if not candidate.is_file():
        raise ValidationError(f"Asset path is not a file: {candidate}")
    return candidate


def detect_file_type(path: Path) -> FileType:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return FileType.MD
    if suffix == ".txt":
        return FileType.TXT
    if suffix == ".docx":
        return FileType.DOCX
    if suffix == ".pptx":
        return FileType.PPTX
    if suffix == ".xlsx":
        return FileType.XLSX
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return FileType.IMAGE
    return FileType.UNKNOWN


def parse_source_category(raw_value: str) -> SourceCategory:
    try:
        return SourceCategory(raw_value)
    except ValueError as exc:
        raise ValidationError(f"Invalid source_category: {raw_value}") from exc


def _safe_parse(path: Path, file_type: FileType):
    try:
        return parse_asset(path, file_type)
    except Exception:
        return ParseResult(
            parser_name="failed_parser",
            status=IngestionStatus.FAILED,
            title=path.stem,
            summary="Asset metadata was recorded, but content extraction failed.",
        )
