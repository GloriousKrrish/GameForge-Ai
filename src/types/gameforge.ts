export interface Asset {
  id: string;
  name: string;
  type: string;
}

export interface GenerationJob {
  id: string;
  prompt: string;
  status: "idle" | "processing" | "completed" | "failed";
  progress: number;
}
