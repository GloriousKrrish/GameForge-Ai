import { Download, Hexagon } from "lucide-react";
import { useEffect, useState } from "react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { checkHealth } from "@/api/health";
import { exportAsset } from "@/api/assets";

const statusLabel: Record<string, string> = {
  idle: "Ready",
  processing: "Generating",
  completed: "Complete",
  failed: "Failed",
};

export function Header() {
  const generationStatus = useGameForgeStore((s) => s.generationStatus);
  const activeAssetUrl = useGameForgeStore((s) => s.activeAssetUrl);
  const currentJobId = useGameForgeStore((s) => s.currentJobId);
  const [backendOnline, setBackendOnline] = useState(false);

  // Poll backend health every 5 seconds
  useEffect(() => {
    let active = true;

    const check = async () => {
      try {
        await checkHealth();
        if (active) setBackendOnline(true);
      } catch {
        if (active) setBackendOnline(false);
      }
    };

    check();
    const timer = setInterval(check, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const handleExport = async () => {
    // Find the asset_id from the store — for now we extract it from the last job
    // In a fuller implementation we'd track asset_id directly
    if (!activeAssetUrl) return;
    try {
      if (currentJobId) {
        const { getJobStatus } = await import("@/api/jobs");
        const job = await getJobStatus(currentJobId);
        if (job.asset_id) {
          await exportAsset(job.asset_id);
        }
      }
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-panel/70 px-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="flex size-8 items-center justify-center rounded-md border border-border bg-secondary text-gold">
          <Hexagon className="size-4" />
        </span>
        <span className="font-serif text-xl tracking-wide text-foreground">
          GameForge <span className="text-gold">AI</span>
        </span>
      </div>

      <div className="hidden items-center gap-4 text-sm text-muted-foreground sm:flex">
        {/* Backend connection status — driven by real health check */}
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`size-1.5 rounded-full ${
              backendOnline
                ? "bg-emerald-400 shadow-[0_0_8px_theme(colors.emerald.400)]"
                : "bg-red-500 shadow-[0_0_8px_theme(colors.red.500)]"
            }`}
          />
          {backendOnline ? "Connected" : "Backend Offline"}
        </div>
        <span className="text-border">|</span>
        <span className="text-xs uppercase tracking-[0.18em]">Project</span>
        <span className="rounded-md border border-border px-2.5 py-1 text-foreground">
          Untitled Scene
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className={`size-1.5 rounded-full ${
              generationStatus === "processing"
                ? "animate-pulse bg-amber-400 shadow-[0_0_8px_theme(colors.amber.400)]"
                : generationStatus === "completed"
                  ? "bg-emerald-400 shadow-[0_0_8px_theme(colors.emerald.400)]"
                  : generationStatus === "failed"
                    ? "bg-red-500 shadow-[0_0_8px_theme(colors.red.500)]"
                    : "bg-gold shadow-[0_0_8px_var(--gold)]"
            }`}
          />
          {statusLabel[generationStatus]}
        </div>
        <button
          onClick={handleExport}
          disabled={!activeAssetUrl}
          className="inline-flex items-center gap-2 rounded-md border border-gold/40 bg-gold/10 px-3 py-1.5 text-sm text-gold transition-colors hover:bg-gold/20 disabled:opacity-40"
        >
          <Download className="size-4" />
          Export
        </button>
      </div>
    </header>
  );
}
