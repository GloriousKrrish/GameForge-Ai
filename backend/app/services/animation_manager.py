"""GameForge AI — Persistent Animation Manager Service.

Manages persistent SQLite state for animation records, enforcing character & rig relationships,
timing bounds, project isolation, and metadata validation.
"""
import json
import math
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.db.database import db
from app.models.domain import (
    AnimationCreateRequest, AnimationModel, AnimationStatus, AnimationType,
    AnimationUpdateRequest, CharacterModel, RigModel,
)
from app.services.character_manager import character_manager

logger = logging.getLogger("gameforge.animation_manager")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnimationValidationError(ValueError):
    """Raised when animation validation, relationship checks, or payload bounds fail."""
    pass


class AnimationManager:
    """Owns persistent animation state and relationship validation."""

    def create_animation(self, character: CharacterModel, req: AnimationCreateRequest) -> AnimationModel:
        """Create a new persistent AnimationModel bound to a Character and optional Rig."""
        if not req.name or not isinstance(req.name, str) or not req.name.strip():
            raise AnimationValidationError("Animation name must be a non-empty string.")
        if len(req.name) > 200:
            raise AnimationValidationError("Animation name exceeds maximum allowed length of 200 characters.")

        if req.project_id != character.project_id:
            raise AnimationValidationError(
                f"Project mismatch: Request project '{req.project_id}' does not match character project '{character.project_id}'."
            )

        rig = None
        if req.rig_id:
            rig = character_manager.get_rig(character.id)
            if not rig or rig.id != req.rig_id or rig.character_id != character.id:
                raise AnimationValidationError(
                    f"Rig '{req.rig_id}' is invalid or does not belong to character '{character.id}'."
                )

        self._validate_timing_bounds(req.duration_seconds, req.fps, req.frame_start, req.frame_end)

        anim_id = f"anim_{uuid.uuid4().hex[:8]}"
        now_time = _now()

        animation = AnimationModel(
            id=anim_id,
            project_id=character.project_id,
            character_id=character.id,
            rig_id=req.rig_id,
            name=req.name.strip(),
            animation_type=req.animation_type,
            status=AnimationStatus.READY,
            duration_seconds=float(req.duration_seconds),
            fps=int(req.fps),
            frame_start=int(req.frame_start),
            frame_end=int(req.frame_end),
            is_looping=bool(req.is_looping),
            metadata=req.metadata or {},
            created_at=now_time,
            updated_at=now_time,
        )

        self.validate_animation_relationship(animation, character, rig)
        self.save_animation(animation)
        logger.info("Animation created & persisted: %s (%s) for character %s", animation.name, animation.id, character.id)
        return animation

    def save_animation(self, animation: AnimationModel) -> AnimationModel:
        """Save or update an AnimationModel in SQLite database."""
        animation.updated_at = _now()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO animations (id, project_id, character_id, rig_id, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    animation.id,
                    animation.project_id,
                    animation.character_id,
                    animation.rig_id,
                    json.dumps(animation.model_dump()),
                    animation.created_at,
                    animation.updated_at,
                ),
            )
        return animation

    def get_animation(self, animation_id: str) -> Optional[AnimationModel]:
        """Fetch animation by ID from SQLite."""
        with db.get_connection() as conn:
            row = conn.execute("SELECT data_json FROM animations WHERE id = ?", (animation_id,)).fetchone()
        return AnimationModel.model_validate(json.loads(row["data_json"])) if row else None

    def list_animations(
        self,
        character_id: Optional[str] = None,
        project_id: str = "proj_default",
    ) -> List[AnimationModel]:
        """List animations filtered by project_id and optional character_id."""
        with db.get_connection() as conn:
            if character_id:
                rows = conn.execute(
                    "SELECT data_json FROM animations WHERE project_id = ? AND character_id = ? ORDER BY created_at DESC",
                    (project_id, character_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT data_json FROM animations WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
        return [AnimationModel.model_validate(json.loads(row["data_json"])) for row in rows]

    def update_animation(self, animation_id: str, req: AnimationUpdateRequest) -> AnimationModel:
        """Update metadata / timing parameters of an existing animation."""
        anim = self.get_animation(animation_id)
        if not anim:
            raise AnimationValidationError(f"Animation '{animation_id}' not found.")

        if req.name is not None:
            if not isinstance(req.name, str) or not req.name.strip():
                raise AnimationValidationError("Updated animation name must be a non-empty string.")
            anim.name = req.name.strip()

        if req.animation_type is not None:
            anim.animation_type = req.animation_type

        new_duration = req.duration_seconds if req.duration_seconds is not None else anim.duration_seconds
        new_fps = req.fps if req.fps is not None else anim.fps
        new_start = req.frame_start if req.frame_start is not None else anim.frame_start
        new_end = req.frame_end if req.frame_end is not None else anim.frame_end

        self._validate_timing_bounds(new_duration, new_fps, new_start, new_end)

        anim.duration_seconds = float(new_duration)
        anim.fps = int(new_fps)
        anim.frame_start = int(new_start)
        anim.frame_end = int(new_end)

        if req.is_looping is not None:
            anim.is_looping = bool(req.is_looping)

        if req.metadata is not None:
            anim.metadata.update(req.metadata)

        character = character_manager.get_character(anim.character_id)
        if not character:
            raise AnimationValidationError(f"Underlying character '{anim.character_id}' not found.")

        self.validate_animation_relationship(anim, character)
        self.save_animation(anim)
        return anim

    def delete_animation(self, animation_id: str) -> bool:
        """Delete an animation by ID from SQLite."""
        with db.get_connection() as conn:
            cur = conn.execute("DELETE FROM animations WHERE id = ?", (animation_id,))
        return cur.rowcount > 0

    def validate_animation_relationship(
        self,
        animation: AnimationModel,
        character: Optional[CharacterModel] = None,
        rig: Optional[RigModel] = None,
    ) -> None:
        """Validate animation relationship integrity, project isolation, and parameter safety."""
        if not character:
            character = character_manager.get_character(animation.character_id)
            if not character:
                raise AnimationValidationError(f"Referenced character '{animation.character_id}' does not exist.")

        if animation.character_id != character.id:
            raise AnimationValidationError("Animation character_id does not match target character.")

        if animation.project_id != character.project_id:
            raise AnimationValidationError("Project isolation boundary error: Animation and Character projects mismatch.")

        if animation.rig_id:
            if not rig:
                rig = character_manager.get_rig(character.id)
            if not rig or rig.id != animation.rig_id or rig.character_id != character.id:
                raise AnimationValidationError(f"Animation rig_id '{animation.rig_id}' is invalid or unlinked.")

        self._validate_timing_bounds(
            animation.duration_seconds, animation.fps, animation.frame_start, animation.frame_end
        )

    @staticmethod
    def _validate_timing_bounds(duration: float, fps: int, frame_start: int, frame_end: int) -> None:
        """Validate numerical timing bounds and ordering."""
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0.0 or duration > 600.0:
            raise AnimationValidationError(f"Invalid duration_seconds '{duration}'. Must be finite positive float <= 600.0.")
        if not isinstance(fps, int) or fps < 1 or fps > 120:
            raise AnimationValidationError(f"Invalid fps '{fps}'. Must be an integer between 1 and 120.")
        if not isinstance(frame_start, int) or frame_start < 0:
            raise AnimationValidationError(f"Invalid frame_start '{frame_start}'. Must be non-negative integer.")
        if not isinstance(frame_end, int) or frame_end < frame_start:
            raise AnimationValidationError(f"Invalid frame_end '{frame_end}'. Must be integer >= frame_start '{frame_start}'.")


animation_manager = AnimationManager()
