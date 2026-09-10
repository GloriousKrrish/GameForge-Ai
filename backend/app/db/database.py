"""GameForge AI — Database Engine (SQLite).

Provides lightweight, robust SQLite persistence for Projects, Scenes, Assets, Jobs, and Execution Graphs.
Uses standard Python sqlite3 with PRAGMA journal_mode=WAL for high reliability.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger("gameforge.db")

DB_PATH = Path(__file__).parent.parent.parent / "gameforge.db"


class Database:
    """Thread-safe SQLite Database Manager."""

    def __init__(self, db_file: Optional[Path] = None):
        self.db_file = db_file or DB_PATH
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self):
        """Initialize database schema tables if they do not exist."""
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    active_scene_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scenes (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    glb_url TEXT NOT NULL,
                    poly_count INTEGER,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    graph_json TEXT,
                    asset_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            logger.info("SQLite database initialized at %s", self.db_file)


db = Database()
