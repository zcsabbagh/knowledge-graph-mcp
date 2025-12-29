"""Database connection management."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from .schema import create_tables

# Default database path
DEFAULT_DB_PATH = Path.home() / ".knowledge_graph" / "knowledge.db"

_db_path: Path = DEFAULT_DB_PATH


def set_db_path(path: Path | str) -> None:
    """Set the database path."""
    global _db_path
    _db_path = Path(path)


def get_db_path() -> Path:
    """Get the current database path."""
    return _db_path


def init_database(path: Path | str | None = None) -> None:
    """Initialize the database, creating tables if needed."""
    if path:
        set_db_path(path)

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        create_tables(cursor)
        conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection as a context manager."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
    finally:
        conn.close()
