"""Minimal connection manager for database operations."""

import sqlite3
from contextlib import contextmanager
from typing import Generator

import requests

from config import config

DB_PATH = config.db_path


@contextmanager
def get_database_pool() -> Generator[sqlite3.Connection, None, None]:
    """Simple database connection context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_session_manager():
    """Get a simple session manager (requests session)."""
    return requests.Session()
