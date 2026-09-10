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
  parent_id?: string | null;
  visible?: boolean;
  created_at?: string;
  updated_at?: string;
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

export async function createSceneObject(data: {
  name: string;
  object_type?: string;
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  color?: string;
  parent_id?: string;
}): Promise<{ success: boolean; object: SceneObjectData; scene: SceneData }> {
  return apiFetch('/api/v1/scenes/objects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSceneObject(
  objectId: string,
  updates: Partial<SceneObjectData> & { position?: [number, number, number]; rotation?: [number, number, number]; scale?: [number, number, number]; color?: string }
): Promise<{ success: boolean; scene: SceneData }> {
  return apiFetch(`/api/v1/scenes/objects/${objectId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function deleteSceneObject(objectId: string): Promise<{ success: boolean; scene: SceneData }> {
  return apiFetch(`/api/v1/scenes/objects/${objectId}`, {
    method: 'DELETE',
  });
}

export async function duplicateSceneObject(objectId: string): Promise<{ success: boolean; duplicate: SceneObjectData; scene: SceneData }> {
  return apiFetch('/api/v1/scenes/objects/duplicate', {
    method: 'POST',
    body: JSON.stringify({ object_id: objectId }),
  });
}

export async function parentSceneObject(childId: string, parentId: string): Promise<{ success: boolean; scene: SceneData }> {
  return apiFetch('/api/v1/scenes/objects/parent', {
    method: 'POST',
    body: JSON.stringify({ child_id: childId, parent_id: parentId }),
  });
}

export async function unparentSceneObject(childId: string): Promise<{ success: boolean; scene: SceneData }> {
  return apiFetch('/api/v1/scenes/objects/unparent', {
    method: 'POST',
    body: JSON.stringify({ child_id: childId }),
  });
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
