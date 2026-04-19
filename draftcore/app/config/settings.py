from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    config_path: Path | None = None
    db_path: Path = Path("draftcore.db")
    output_dir: Path = Path("output")


def load_settings(config_path: str | None = None) -> AppSettings:
    return AppSettings(config_path=Path(config_path) if config_path else None)
