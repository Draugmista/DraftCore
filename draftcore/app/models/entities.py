from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from draftcore.app.models.enums import FileType, IngestionStatus, ProjectStatus, SourceCategory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportProject(SQLModel, table=True):
    __tablename__ = "report_projects"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    topic: str
    target_output: str
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    path: str = Field(unique=True, index=True)
    file_type: FileType = Field(index=True)
    source_category: SourceCategory = Field(index=True)
    topic_or_task: str | None = None
    usage_note: str | None = None
    ingestion_status: IngestionStatus = Field(default=IngestionStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AssetContentProfile(SQLModel, table=True):
    __tablename__ = "asset_content_profiles"

    asset_id: int = Field(foreign_key="assets.id", primary_key=True)
    title: str | None = None
    summary: str | None = None
    searchable_text: str | None = None
    structure_excerpt: str | None = None
    page_count: int | None = None
    paragraph_count: int | None = None
    parser_name: str
    extracted_at: datetime = Field(default_factory=utc_now)


class ProjectAsset(SQLModel, table=True):
    __tablename__ = "project_assets"

    project_id: int = Field(foreign_key="report_projects.id", primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", primary_key=True)
    relation_note: str | None = None
    linked_at: datetime = Field(default_factory=utc_now)


class AssetWithProfile(SQLModel):
    asset: Asset
    profile: Optional[AssetContentProfile] = None
