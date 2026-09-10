import { apiFetch } from "./client";

export interface MaterialData {
  id: string;
  name: string;
  base_color: number[];
  metallic: number;
  roughness: number;
  emission_color: number[];
  emission_strength: number;
  opacity: number;
  alpha_mode: "OPAQUE" | "MASK" | "BLEND";
  double_sided: boolean;
  texture_ids: string[];
  created_at?: string;
  updated_at?: string;
}

export interface MaterialCreatePayload {
  name: string;
  base_color?: number[];
  metallic?: number;
  roughness?: number;
  emission_color?: number[];
  emission_strength?: number;
  opacity?: number;
  alpha_mode?: "OPAQUE" | "MASK" | "BLEND";
  double_sided?: boolean;
}

export interface MaterialUpdatePayload {
  name?: string;
  base_color?: number[];
  metallic?: number;
  roughness?: number;
  emission_color?: number[];
  emission_strength?: number;
  opacity?: number;
  alpha_mode?: "OPAQUE" | "MASK" | "BLEND";
  double_sided?: boolean;
}

export async function listMaterials(): Promise<MaterialData[]> {
  return apiFetch<MaterialData[]>("/api/v1/materials");
}

export async function getMaterial(materialId: string): Promise<MaterialData> {
  return apiFetch<MaterialData>(`/api/v1/materials/${materialId}`);
}

export async function createMaterial(payload: MaterialCreatePayload): Promise<MaterialData> {
  return apiFetch<MaterialData>("/api/v1/materials", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMaterial(materialId: string, payload: MaterialUpdatePayload): Promise<MaterialData> {
  return apiFetch<MaterialData>(`/api/v1/materials/${materialId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteMaterial(materialId: string): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(`/api/v1/materials/${materialId}`, {
    method: "DELETE",
  });
}

export async function assignMaterialToObject(objectId: string, materialId: string): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(`/api/v1/scenes/objects/${objectId}/material`, {
    method: "POST",
    body: JSON.stringify({ material_id: materialId }),
  });
}

export async function unassignMaterialFromObject(objectId: string): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(`/api/v1/scenes/objects/${objectId}/material`, {
    method: "DELETE",
  });
}
