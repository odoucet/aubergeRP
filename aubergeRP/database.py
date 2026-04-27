"""SQLite database setup and session management for aubergeRP.

All persistent data (characters, conversations, messages) is stored in a
single SQLite file at ``{data_dir}/auberge.db``.  The schema is managed by a
lightweight numbered-migration system — see :mod:`aubergeRP.migrations`.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

_engine: Engine | None = None
_engine_data_dir: Path | None = None
_initialized_dirs: set[Path] = set()


def get_engine(data_dir: str | Path | None = None) -> Engine:
    """Return (and lazily create) the shared SQLite engine.

    On the first call *data_dir* must be provided so the engine can be
    initialised.  Subsequent calls may omit it, or pass the same data_dir
    to reuse the existing engine.  If a *different* data_dir is given the
    engine is recreated (useful in tests).
    """
    global _engine, _engine_data_dir
    if data_dir is not None:
        resolved = Path(data_dir)
        if _engine is None or _engine_data_dir != resolved:
            if _engine is not None:
                _engine.dispose()
            db_path = resolved / "auberge.db"
            _engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
            )
            _engine_data_dir = resolved
    if _engine is None:
        raise RuntimeError("Database engine has not been initialised yet")
    return _engine


def reset_engine() -> None:
    """Reset the singleton engine (used in tests)."""
    global _engine, _engine_data_dir, _initialized_dirs
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _engine_data_dir = None
    _initialized_dirs = set()


def init_db(data_dir: str | Path) -> None:
    """Initialise the database and run pending migrations.

    This is idempotent — subsequent calls for the same *data_dir* are
    fast no-ops after the first successful initialisation.
    """
    from aubergeRP.migrations import run_migrations  # local import to avoid cycles

    resolved = Path(data_dir)
    engine = get_engine(resolved)
    if resolved in _initialized_dirs:
        return
    SQLModel.metadata.create_all(engine)
    run_migrations(engine, resolved)
    _initialized_dirs.add(resolved)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    with Session(get_engine()) as session:
        yield session
