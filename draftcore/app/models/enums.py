from __future__ import annotations

from enum import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FileType(StrEnum):
    MD = "md"
    TXT = "txt"
    DOCX = "docx"
    PPTX = "pptx"
    IMAGE = "image"
    XLSX = "xlsx"
    UNKNOWN = "unknown"


class SourceCategory(StrEnum):
    RAW = "raw"
    TEMPLATE = "template"
    REFERENCE = "reference"


class IngestionStatus(StrEnum):
    PENDING = "pending"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class ReuseCandidateType(StrEnum):
    STRUCTURE = "structure"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    EXPRESSION = "expression"
    PATH_REFERENCE = "path_reference"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class OutputFormat(StrEnum):
    MARKDOWN = "markdown"
    DOCX = "docx"
