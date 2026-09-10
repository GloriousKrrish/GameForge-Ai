/**
 * GameForge AI — Generation API calls.
 */
import { apiFetch } from "./client";

export interface GenerateResponse {
  id: string;
  prompt: string;
  status: string;
  progress: number;
  current_step: string | null;
  asset_url: string | null;
  asset_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export async function generateAsset(prompt: string): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/v1/generate", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}
