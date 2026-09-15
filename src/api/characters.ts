import { apiFetch } from "./client";

export type CharacterType = "HUMANOID" | "QUADRUPED" | "CREATURE" | "CUSTOM";
export type CharacterStatus = "UNCLASSIFIED" | "CLASSIFIED" | "RIGGING" | "RIGGED" | "SKINNING" | "READY" | "FAILED";

export interface CharacterData {
  id: string;
  project_id: string;
  asset_id: string;
  name: string;
  character_type: CharacterType;
  status: CharacterStatus;
  rig_id?: string | null;
  skeleton_id?: string | null;
  skinning?: { skeleton_id: string; vertex_count: number; max_influences_per_vertex: number; status: string } | null;
  scene_object_ids: string[];
}

export interface SkeletonData {
  id: string;
  character_id: string;
  name: string;
  root_bone_id: string;
  bone_count: number;
  bones: Array<{ id: string; name: string; parent_id?: string | null; head: number[]; tail: number[] }>;
}

export async function listCharacters(projectId = "proj_default") {
  return apiFetch<CharacterData[]>(`/api/v1/characters?project_id=${encodeURIComponent(projectId)}`);
}

export async function createCharacter(payload: { asset_id: string; name: string; character_type: CharacterType; project_id?: string }) {
  return apiFetch<CharacterData>("/api/v1/characters", { method: "POST", body: JSON.stringify(payload) });
}

export async function rigCharacter(characterId: string, payload?: { rig_type?: "HUMANOID" | "GENERIC" | "CUSTOM"; auto_weight?: boolean }) {
  return apiFetch<{ character: CharacterData; rig: unknown; skeleton: SkeletonData }>(`/api/v1/characters/${characterId}/rig`, {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export async function getCharacterSkeleton(characterId: string) {
  return apiFetch<SkeletonData>(`/api/v1/characters/${characterId}/skeleton`);
}

export async function instantiateCharacterInScene(characterId: string, payload?: { name?: string; position?: number[]; rotation?: number[]; scale?: number[] }) {
  return apiFetch<{ success: boolean; scene: any; instantiated_object: any; glb_url: string }>(`/api/v1/characters/${characterId}/instantiate`, {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export async function deleteCharacter(characterId: string) {
  return apiFetch<{ success: boolean }>(`/api/v1/characters/${characterId}`, {
    method: "DELETE",
  });
}

export async function inspectCharacterGlb(characterId: string) {
  return apiFetch<any>(`/api/v1/characters/${characterId}/inspect_glb`);
}