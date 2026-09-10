/**
 * GameForge AI — Assets API calls.
 */
import { apiFetch, API_BASE_URL } from "./client";

export interface AssetData {
  id: string;
  name: string;
  type: string;
  glb_url: string;
  thumbnail_url: string | null;
  poly_count: number | null;
  created_at: string;
}

export async function listAssets(): Promise<AssetData[]> {
  return apiFetch<AssetData[]>("/api/v1/assets");
}

export async function getAsset(assetId: string): Promise<AssetData> {
  return apiFetch<AssetData>(`/api/v1/assets/${assetId}`);
}

export async function exportAsset(assetId: string): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/export`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ asset_id: assetId }),
  });

  if (!res.ok) {
    throw new Error(`Export failed: ${res.status}`);
  }

  // Trigger browser download
  const blob = await res.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = `gameforge_export.glb`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(downloadUrl);
}
