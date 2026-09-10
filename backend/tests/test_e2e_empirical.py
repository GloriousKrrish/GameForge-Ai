"""GameForge AI — End-to-End Empirical Verification Test.
Executes real full-stack request flow: generation, GLB creation, transform updates, SQLite persistence, and failure lifecycle.
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import process_generation_job
from app.db.database import db
from app.services.job_manager import job_manager
from app.schemas.execution_graph import ExecutionGraph, JobStatus


def test_e2e_generation_pipeline():
    client = TestClient(app)
    
    # 1. POST /generate
    resp = client.post("/api/v1/generate", json={"prompt": "Create a large red cube"})
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    # Process job synchronously
    process_generation_job(job_id)

    # Poll status
    job_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    res_data = job_resp.json()
    assert res_data["status"] == "COMPLETED"
    
    glb_url = res_data["asset_url"]
    public_exports_dir = Path(__file__).resolve().parents[2] / "public" / "exports"
    glb_file = public_exports_dir / glb_url.lstrip("/exports/")
    assert glb_file.exists()
    assert glb_file.stat().st_size > 0


def test_e2e_properties_transform_pipeline():
    client = TestClient(app)
    
    tf_resp = client.post("/api/v1/scenes/objects/transform", json={
        "object_name": "GameForge_Cube",
        "position": [2.0, 0.0, 0.0],
        "rotation": [0.0, 45.0, 0.0],
        "scale": [1.5, 1.5, 1.5]
    })
    assert tf_resp.status_code == 200
    tf_data = tf_resp.json()
    assert tf_data["success"] is True
    assert tf_data["glb_url"].startswith("/exports/")

    # Check persistence in SQLite
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM scenes WHERE id = 'scene_default'").fetchone()
    assert row is not None
    data = json.loads(row["data_json"])
    assert data["objects"][0]["transform"]["position"] == [2.0, 0.0, 0.0]


def test_e2e_job_failure_lifecycle():
    bad_job = job_manager.create_job("Bad Job", ExecutionGraph(id="bad_g", steps=[]))
    process_generation_job(bad_job.id)
    failed_job = job_manager.get_job(bad_job.id)
    assert failed_job.status == JobStatus.FAILED
    assert "Graph Validation Error" in failed_job.error
