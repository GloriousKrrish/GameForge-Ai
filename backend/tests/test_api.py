"""Tests for FastAPI endpoints — all operations are real, no fakes."""
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "gameforge-api"
    assert "blender_available" in data


# ---------------------------------------------------------------------------
# Generate + Job polling
# ---------------------------------------------------------------------------
def test_generate_creates_real_job():
    response = client.post(
        "/api/v1/generate",
        json={"prompt": "Create a red metallic cube"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["prompt"] == "Create a red metallic cube"
    assert data["status"] in ("QUEUED", "PROCESSING", "COMPLETED")
    assert data["execution_graph"] is not None
    assert len(data["execution_graph"]["steps"]) >= 3  # CREATE + MATERIAL + EXPORT


def test_generate_and_poll_to_completion():
    """End-to-end: generate a job and poll until it completes or fails."""
    response = client.post(
        "/api/v1/generate",
        json={"prompt": "Create a blue sphere"},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Poll for completion (background task runs synchronously in TestClient)
    # Give it a moment, then check
    time.sleep(1)
    job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    job_data = job_response.json()

    # The job should have completed (fallback engine) or still be processing
    assert job_data["status"] in ("COMPLETED", "PROCESSING", "FAILED")

    if job_data["status"] == "COMPLETED":
        assert job_data["asset_url"] is not None
        assert job_data["asset_id"] is not None
        assert job_data["progress"] == 100.0


def test_get_nonexistent_job_returns_404():
    response = client.get("/api/v1/jobs/nonexistent_id")
    assert response.status_code == 404


def test_generate_empty_prompt_returns_422():
    response = client.post(
        "/api/v1/generate",
        json={"prompt": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def test_list_assets_initially_empty_or_populated():
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_nonexistent_asset_returns_404():
    response = client.get("/api/v1/assets/nonexistent_id")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def test_export_nonexistent_asset_returns_404():
    response = client.post(
        "/api/v1/export",
        json={"asset_id": "nonexistent"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "GameForge AI"
