/**
 * GameForge AI — Job Status API calls.
 */
import { apiFetch } from "./client";
import type { GenerateResponse } from "./generation";

export async function getJobStatus(jobId: string): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>(`/api/v1/jobs/${jobId}`);
}
