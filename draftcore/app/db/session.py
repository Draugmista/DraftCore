from __future__ import annotations

from sqlmodel import SQLModel, create_engine


def build_engine(db_url: str = "sqlite:///draftcore.db"):
    return create_engine(db_url, echo=False)


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)
