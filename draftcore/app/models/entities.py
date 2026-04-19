from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from draftcore.app.models.enums import (
    FileType,
    IngestionStatus,
    ProjectStatus,
    ReuseCandidateType,
    SourceCategory,
)


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


class AssetCollection(SQLModel, table=True):
    __tablename__ = "asset_collections"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_asset_collections_project_name"),)

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="report_projects.id", index=True)
    name: str
    purpose: str
    created_at: datetime = Field(default_factory=utc_now)


class AssetCollectionItem(SQLModel, table=True):
    __tablename__ = "asset_collection_items"

    collection_id: int = Field(foreign_key="asset_collections.id", primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", primary_key=True)
    usage_note: str
    is_candidate: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ReuseCandidate(SQLModel, table=True):
    __tablename__ = "reuse_candidates"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="report_projects.id", index=True)
    asset_id: int = Field(foreign_key="assets.id", index=True)
    candidate_type: ReuseCandidateType = Field(index=True)
    snippet: str
    reason: str
    score_hint: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class AssetWithProfile(SQLModel):
    asset: Asset
    profile: Optional[AssetContentProfile] = None
