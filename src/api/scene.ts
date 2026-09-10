import { apiFetch } from './client';

export interface SceneObjectTransform {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
}

export interface SceneObjectData {
  id: string;
  name: string;
  object_type: string;
  transform: SceneObjectTransform;
  material?: {
    color: string;
    metallic: number;
    roughness: number;
  };
}

export interface SceneData {
  id: string;
  project_id: string;
  name: string;
  objects: SceneObjectData[];
  active_asset_url?: string;
}

export interface TransformUpdateResponse {
  success: boolean;
  scene: SceneData;
  glb_url: string;
  message: string;
}

export async function getActiveScene(): Promise<SceneData> {
  return apiFetch<SceneData>('/api/v1/scenes/active');
}

export async function updateObjectTransform(
  objectName: string,
  transform: {
    position?: [number, number, number];
    rotation?: [number, number, number];
    scale?: [number, number, number];
  }
): Promise<TransformUpdateResponse> {
  return apiFetch<TransformUpdateResponse>('/api/v1/scenes/objects/transform', {
    method: 'POST',
    body: JSON.stringify({
      object_name: objectName,
      ...transform,
    }),
  });
}
