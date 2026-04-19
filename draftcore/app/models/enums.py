from __future__ import annotations

from enum import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class OutputFormat(StrEnum):
    MARKDOWN = "markdown"
    DOCX = "docx"
