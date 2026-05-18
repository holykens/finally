"""Database layer for FinAlly.

Public API:
- :func:`init_db` — create tables and seed default data (idempotent).
- :func:`get_connection` — async context manager for a SQLite connection.
- :func:`get_db_path` — resolve the on-disk path for the SQLite file.
"""

from .database import get_connection, get_db_path, init_db

__all__ = ["get_connection", "get_db_path", "init_db"]
