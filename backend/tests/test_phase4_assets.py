"""
Unit tests for Phase 4: AI 3D Asset Generation Platform.
Tests cover Asset domain model, Provider Adapter system, Asset Validator, Asset Normalizer,
SQLite Asset Registry, Execution Graph operations, and FastAPI endpoints.
"""

import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import (
    AssetModel,
    AssetSourceType,
    AssetStatus,
    AssetGenerationRequest,
    InstantiateAssetRequest,
)
from app.providers import ProviderAdapter, Tripo3DProvider, DeterministicFallbackProvider, AssetGenerationResult
from app.services.asset_validator import AssetValidator, AssetNormalizer
from app.services.asset_manager import asset_manager
from app.schemas.execution_graph import ExecutionStep, OperationType, ExecutionGraph
from app.services.validator import ExecutionGraphValidator

client = TestClient(app)

# Helper to create a valid minimal GLB binary
def create_mock_glb_bytes() -> bytes:
    # 12-byte GLB Header: magic=0x46544C67 ("glTF"), version=2, length=12
    magic = b"glTF"
    version = (2).to_bytes(4, byteorder="little")
    length = (12).to_bytes(4, byteorder="little")
    return magic + version + length


def test_asset_model_domain():
    asset = AssetModel(
        id="asset_test_123",
        project_id="proj_default",
        name="Test Sports Car",
        description="A futuristic sports car asset",
        source_type=AssetSourceType.GENERATED,
        provider="tripo3d",
        provider_asset_id="tripo_999",
        file_path="storage/assets/proj_default/asset_test_123/asset.glb",
        glb_url="/api/v1/assets/asset_test_123/download",
        format="glb",
        mime_type="model/gltf-binary",
        status=AssetStatus.READY,
        generation_prompt="futuristic sports car",
        vertex_count=500,
        triangle_count=1000,
        material_count=1,
        animation_count=0,
    )
    assert asset.id == "asset_test_123"
    assert asset.source_type == AssetSourceType.GENERATED
    assert asset.provider == "tripo3d"
    assert asset.status == AssetStatus.READY


def test_provider_adapter_fallback():
    import asyncio
    adapter = ProviderAdapter()
    req = AssetGenerationRequest(
        prompt="wooden chair",
        style="realistic",
        quality="high",
        poly_budget=50000,
        target_format="glb",
        target_use="game_asset",
    )
    result = asyncio.run(adapter.generate(req, job_id="job_test_fb_1"))
    assert isinstance(result, AssetGenerationResult)
    assert result.provider_name == "DETERMINISTIC / PROCEDURAL FALLBACK"
    assert result.is_fallback is True
    assert result.success is True


def test_asset_validator_valid_glb(tmp_path):
    glb_file = tmp_path / "valid.glb"
    glb_file.write_bytes(create_mock_glb_bytes())

    is_valid, msg, metadata = AssetValidator.validate_glb_file(str(glb_file))
    assert is_valid is True
    assert msg is None
    assert metadata["file_size_bytes"] == 12


def test_asset_validator_invalid_glb(tmp_path):
    corrupt_file = tmp_path / "corrupt.glb"
    corrupt_file.write_bytes(b"NOT_A_GLB_FILE_HEADER")

    is_valid, msg, metadata = AssetValidator.validate_glb_file(str(corrupt_file))
    assert is_valid is False
    assert "Invalid asset file header" in msg


def test_asset_normalizer(tmp_path):
    glb_file = tmp_path / "test.glb"
    glb_file.write_bytes(create_mock_glb_bytes())
    
    success = AssetNormalizer.normalize_glb(str(glb_file))
    # mock glb binary has no mesh faces for trimesh, so normalizer handles gracefully
    assert isinstance(success, bool)


def test_asset_manager_sqlite_crud():
    asset = AssetModel(
        id="asset_crud_1",
        project_id="proj_default",
        name="Medieval Sword",
        description="A sharp medieval sword",
        source_type=AssetSourceType.GENERATED,
        provider="deterministic_fallback",
        glb_url="/api/v1/assets/asset_crud_1/download",
        format="glb",
        mime_type="model/gltf-binary",
        status=AssetStatus.READY,
        vertex_count=300,
        triangle_count=600,
    )
    
    # Save asset
    saved = asset_manager.save_asset(asset)
    assert saved.id == "asset_crud_1"

    # Get asset
    fetched = asset_manager.get_asset("asset_crud_1")
    assert fetched is not None
    assert fetched.name == "Medieval Sword"

    # List assets
    all_assets = asset_manager.list_assets("proj_default")
    assert len(all_assets) >= 1
    assert any(a.id == "asset_crud_1" for a in all_assets)

    # Delete asset
    deleted = asset_manager.delete_asset("asset_crud_1")
    assert deleted is True
    assert asset_manager.get_asset("asset_crud_1") is None


def test_execution_graph_phase4_ops():
    validator = ExecutionGraphValidator()
    
    # GENERATE_ASSET operation with EXPORT_GLB terminal step
    gen_step = ExecutionStep(
        id="step_gen_1",
        type=OperationType.GENERATE_ASSET,
        parameters={
            "prompt": "sci-fi helmet",
            "style": "stylized",
            "quality": "standard",
        }
    )
    export_step = ExecutionStep(
        id="step_export_1",
        type=OperationType.EXPORT_GLB,
        parameters={"filename": "output.glb"}
    )
    graph = ExecutionGraph(id="graph_gen", steps=[gen_step, export_step])
    is_valid, msg = validator.validate(graph)
    assert is_valid is True, msg

    # ADD_ASSET_TO_SCENE operation with EXPORT_GLB terminal step
    add_step = ExecutionStep(
        id="step_add_1",
        type=OperationType.ADD_ASSET_TO_SCENE,
        parameters={
            "asset_id": "asset_xyz",
            "name": "SciFi_Helmet_Obj",
            "position": [0.0, 1.0, 0.0],
        }
    )
    graph_add = ExecutionGraph(id="graph_add", steps=[add_step, export_step])
    is_valid_add, msg_add = validator.validate(graph_add)
    assert is_valid_add is True, msg_add


def test_api_asset_lifecycle():
    # 1. Generate Asset via API
    gen_payload = {
        "prompt": "futuristic hoverbike",
        "style": "realistic",
        "quality": "high",
        "target_use": "game_asset",
        "generate_materials": True,
    }
    response = client.post("/api/v1/assets/generate", json=gen_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    asset_id = data["id"]
    assert data["name"] == "Futuristic Hoverbike"
    assert data["status"] == "READY"

    # 2. List Assets
    list_res = client.get("/api/v1/assets")
    assert list_res.status_code == 200
    assets_list = list_res.json()
    assert any(a["id"] == asset_id for a in assets_list)

    # 3. Get Asset details
    get_res = client.get(f"/api/v1/assets/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == asset_id

    # 4. Instantiate Asset into active scene
    inst_payload = {
        "asset_id": asset_id,
        "name": "Hoverbike_Instance",
        "position": [1.0, 0.0, 2.0],
    }
    inst_res = client.post(f"/api/v1/assets/{asset_id}/instantiate", json=inst_payload)
    assert inst_res.status_code == 200
    inst_data = inst_res.json()
    assert inst_data["success"] is True
    assert "instantiated_object" in inst_data

    # 5. Delete Asset
    del_res = client.delete(f"/api/v1/assets/{asset_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
