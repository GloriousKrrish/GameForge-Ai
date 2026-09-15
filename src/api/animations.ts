import { apiFetch } from "./client";

export type AnimationType = "IDLE" | "WALK" | "RUN" | "WAVE" | "JUMP" | "PROCEDURAL" | "CUSTOM";
export type AnimationStatus = "PENDING" | "GENERATING" | "READY" | "FAILED";

export interface AnimationData {
  id: string;
  project_id: string;
  character_id: string;
  rig_id?: string | null;
  name: string;
  animation_type: AnimationType;
  status: AnimationStatus;
  duration_seconds: number;
  fps: number;
  frame_start: number;
  frame_end: number;
  is_looping: boolean;
  glb_url?: string | null;
  track_count: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export async function listCharacterAnimations(characterId: string, projectId = "proj_default") {
  return apiFetch<AnimationData[]>(`/api/v1/characters/${characterId}/animations?project_id=${encodeURIComponent(projectId)}`);
}

export async function createAnimation(characterId: string, payload: {
  character_id: string;
  name: string;
  animation_type?: AnimationType;
  rig_id?: string | null;
  duration_seconds?: number;
  fps?: number;
  frame_start?: number;
  frame_end?: number;
  is_looping?: boolean;
  project_id?: string;
  metadata?: Record<string, any>;
}) {
  return apiFetch<AnimationData>(`/api/v1/characters/${characterId}/animations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAnimation(animationId: string) {
  return apiFetch<AnimationData>(`/api/v1/animations/${animationId}`);
}

export async function updateAnimation(animationId: string, payload: {
  name?: string;
  animation_type?: AnimationType;
  duration_seconds?: number;
  fps?: number;
  frame_start?: number;
  frame_end?: number;
  is_looping?: boolean;
  metadata?: Record<string, any>;
}) {
  return apiFetch<AnimationData>(`/api/v1/animations/${animationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteAnimation(animationId: string) {
  return apiFetch<{ success: boolean }>(`/api/v1/animations/${animationId}`, {
    method: "DELETE",
  });
}
