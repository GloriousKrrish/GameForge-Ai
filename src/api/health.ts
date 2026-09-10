/**
 * GameForge AI — Health Check API.
 */
import { API_BASE_URL } from "./client";

export interface HealthStatus {
  status: string;
  service: string;
  blender_available: boolean;
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}
