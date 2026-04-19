from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from draftcore.app.config.settings import AppSettings


def build_engine(settings: AppSettings):
    settings.database.path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{settings.database.path.as_posix()}"
    return create_engine(db_url, echo=settings.database.echo)


def init_db(engine) -> None:
    import draftcore.app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(settings: AppSettings):
    engine = build_engine(settings)
    init_db(engine)
    with Session(engine) as session:
        yield session
