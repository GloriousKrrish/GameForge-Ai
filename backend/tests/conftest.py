"""Pytest configuration and database fixtures for GameForge AI tests."""
import os
import tempfile
from pathlib import Path
import pytest
from app.db.database import db

@pytest.fixture(autouse=True)
def reset_db():
    """Reset DB tables before each test to ensure a clean state."""
    with db.get_connection() as conn:
        conn.execute("DELETE FROM scenes")
        conn.execute("DELETE FROM projects")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM jobs")
    yield
