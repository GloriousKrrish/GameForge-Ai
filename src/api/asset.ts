import { apiFetch } from "./client";

export interface AssetModelData {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  source_type: "GENERATED" | "IMPORTED" | "PROCEDURAL" | "SYSTEM";
  provider: string;
  provider_asset_id?: string;
  glb_url: string;
  format: string;
  mime_type: string;
  thumbnail_path?: string;
  status: "PENDING" | "VALIDATING" | "READY" | "FAILED";
  generation_prompt?: string;
  vertex_count: number;
  triangle_count: number;
  material_count: number;
  animation_count: number;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface AssetGenerationPayload {
  prompt: string;
  style?: "realistic" | "stylized" | "low-poly";
  quality?: "draft" | "standard" | "high";
  poly_budget?: number;
  target_format?: string;
  target_use?: string;
  generate_materials?: boolean;
}

export async function listAssets(filters?: { source_type?: string; provider?: string }): Promise<AssetModelData[]> {
  let path = "/api/v1/assets";
  if (filters?.source_type || filters?.provider) {
    const params = new URLSearchParams();
    if (filters.source_type) params.append("source_type", filters.source_type);
    if (filters.provider) params.append("provider", filters.provider);
    path += `?${params.toString()}`;
  }
  return apiFetch<AssetModelData[]>(path);
}

export async function getAsset(assetId: string): Promise<AssetModelData> {
  return apiFetch<AssetModelData>(`/api/v1/assets/${assetId}`);
}

export async function generateAsset3D(payload: AssetGenerationPayload): Promise<AssetModelData> {
  return apiFetch<AssetModelData>("/api/v1/assets/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function instantiateAssetInScene(
  assetId: string,
  options?: { name?: string; position?: number[]; rotation?: number[]; scale?: number[] }
): Promise<{ success: boolean; scene: any; instantiated_object: any; glb_url: string }> {
  return apiFetch<{ success: boolean; scene: any; instantiated_object: any; glb_url: string }>(
    `/api/v1/assets/${assetId}/instantiate`,
    {
      method: "POST",
      body: JSON.stringify({ asset_id: assetId, ...options }),
    }
  );
}

export async function deleteAsset(assetId: string): Promise<{ success: boolean }> {
  return apiFetch<{ success: boolean }>(`/api/v1/assets/${assetId}`, {
    method: "DELETE",
  });
}
