import { create } from "zustand";
import type { Asset, GenerationJob } from "@/types/gameforge";

interface GameForgeState {
  selectedAsset: Asset | null;
  prompt: string;
  generationStatus: GenerationJob["status"];
  progress: number;
  activeAssetUrl: string | null;
  currentJobId: string | null;
  objectStats: { objects: number; tris: number };
  errorMessage: string | null;

  selectedObjectId: string | null;
  activeSceneData: any | null;

  selectedObject: {
    name: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
  };
  sceneObjects: Array<{
    id: string;
    name: string;
    type: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
    parent_id?: string | null;
    visible?: boolean;
  }>;

  setSelectedObjectId: (id: string | null) => void;
  setActiveSceneData: (data: any) => void;
  setSelectedObject: (obj: {
    name: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
  }) => void;
  setSceneObjects: (objs: Array<{
    id: string;
    name: string;
    type: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
    parent_id?: string | null;
    visible?: boolean;
  }>) => void;
  setSelectedAsset: (asset: Asset | null) => void;
  setPrompt: (prompt: string) => void;
  setGenerationStatus: (status: GenerationJob["status"]) => void;
  setProgress: (progress: number) => void;
  setActiveAssetUrl: (url: string | null) => void;
  setCurrentJobId: (id: string | null) => void;
  setObjectStats: (stats: { objects: number; tris: number }) => void;
  setErrorMessage: (msg: string | null) => void;
}

export const useGameForgeStore = create<GameForgeState>((set) => ({
  selectedAsset: null,
  prompt: "",
  generationStatus: "idle",
  progress: 0,
  activeAssetUrl: null,
  currentJobId: null,
  objectStats: { objects: 0, tris: 0 },
  errorMessage: null,
  selectedObjectId: "obj_default_cube",
  activeSceneData: null,

  selectedObject: {
    name: "GameForge_Cube",
    position: [0, 0, 0] as [number, number, number],
    rotation: [0, 0, 0] as [number, number, number],
    scale: [1, 1, 1] as [number, number, number],
  },
  sceneObjects: [
    {
      id: "obj_default_cube",
      name: "GameForge_Cube",
      type: "CUBE",
      position: [0, 0, 0] as [number, number, number],
      rotation: [0, 0, 0] as [number, number, number],
      scale: [1, 1, 1] as [number, number, number],
      visible: true,
    }
  ],
  setSelectedObjectId: (selectedObjectId) => set({ selectedObjectId }),
  setActiveSceneData: (activeSceneData) => set({ activeSceneData }),
  setSelectedObject: (selectedObject) => set({ selectedObject }),
  setSceneObjects: (sceneObjects) => set({ sceneObjects }),
  setSelectedAsset: (selectedAsset) => set({ selectedAsset }),
  setPrompt: (prompt) => set({ prompt }),
  setGenerationStatus: (generationStatus) => set({ generationStatus }),
  setProgress: (progress) => set({ progress }),
  setActiveAssetUrl: (activeAssetUrl) => set({ activeAssetUrl }),
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setObjectStats: (objectStats) => set({ objectStats }),
  setErrorMessage: (errorMessage) => set({ errorMessage }),
}));
