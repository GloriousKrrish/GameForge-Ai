"""GameForge AI — Automated Tests for Domain Models & Database Persistence.
"""
import pytest
from app.db.repositories import SceneRepository
from app.models.domain import Scene, SceneObject


def test_get_or_create_default_scene():
    scene = SceneRepository.get_or_create_default_scene()
    assert scene is not None
    assert scene.id == "scene_default"
    assert len(scene.objects) >= 1
    assert scene.objects[0].name == "GameForge_Cube"


def test_update_object_transform():
    scene = SceneRepository.get_or_create_default_scene()
    updated = SceneRepository.update_object_transform(
        scene_id=scene.id,
        object_name="GameForge_Cube",
        position=[2.5, 0.0, 1.0],
        rotation=[0.0, 45.0, 0.0],
        scale=[2.0, 2.0, 2.0],
    )
    assert updated is not None
    obj = updated.objects[0]
    assert obj.transform.position == [2.5, 0.0, 1.0]
    assert obj.transform.rotation == [0.0, 45.0, 0.0]
    assert obj.transform.scale == [2.0, 2.0, 2.0]
