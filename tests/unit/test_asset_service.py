from __future__ import annotations

from pathlib import Path

import pytest

from draftcore.app.models.enums import FileType, IngestionStatus, SourceCategory
from draftcore.app.parsers import parse_asset
from draftcore.app.services.asset_service import detect_file_type, normalize_asset_path, parse_source_category
from draftcore.app.services.errors import ValidationError


def test_normalize_asset_path_requires_existing_file() -> None:
    file_path = Path("samples/assets/workflow-raw-01.md").resolve()

    resolved = normalize_asset_path(str(file_path))

    assert resolved == file_path.resolve()


def test_normalize_asset_path_rejects_missing_file() -> None:
    with pytest.raises(ValidationError):
        normalize_asset_path(str(Path("samples/assets/missing.md").resolve()))


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("note.md", FileType.MD),
        ("report.txt", FileType.TXT),
        ("slides.pptx", FileType.PPTX),
        ("brief.docx", FileType.DOCX),
        ("sheet.xlsx", FileType.XLSX),
        ("photo.png", FileType.IMAGE),
        ("blob.bin", FileType.UNKNOWN),
    ],
)
def test_detect_file_type(filename: str, expected: FileType) -> None:
    assert detect_file_type(Path(filename)) == expected


def test_parse_source_category_validates_values() -> None:
    assert parse_source_category("template") == SourceCategory.TEMPLATE
    with pytest.raises(ValidationError):
        parse_source_category("history")


def test_parse_asset_for_text_file_returns_searchable_content() -> None:
    file_path = Path("samples/assets/workflow-raw-01.md").resolve()

    result = parse_asset(file_path, FileType.MD)

    assert result.status == IngestionStatus.PARSED
    assert result.title == "# Quarterly Input"
    assert result.searchable_text is not None
    assert "Revenue improved" in result.searchable_text


def test_parse_asset_for_unknown_file_stays_degraded() -> None:
    file_path = Path("samples/assets/parser-unknown-01.bin").resolve()

    result = parse_asset(file_path, FileType.UNKNOWN)

    assert result.status == IngestionStatus.PENDING
    assert "No parser" in result.summary
