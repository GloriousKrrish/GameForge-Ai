import { Sparkles, Box, Palette, Play, Camera, Loader2 } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { generateAsset } from "@/api/generation";
import { getJobStatus } from "@/api/jobs";

const quickActions = [
  { label: "Red Metallic Cube", prompt: "Create a red metallic cube", icon: Box },
  { label: "Blue Shiny Sphere", prompt: "Create a blue shiny sphere", icon: Palette },
  { label: "Gold Cube", prompt: "Create a gold cube", icon: Play },
  { label: "Green Sphere", prompt: "Create a green sphere", icon: Camera },
];

export function CommandBar() {
  const prompt = useGameForgeStore((s) => s.prompt);
  const setPrompt = useGameForgeStore((s) => s.setPrompt);
  const generationStatus = useGameForgeStore((s) => s.generationStatus);
  const setGenerationStatus = useGameForgeStore((s) => s.setGenerationStatus);
  const setActiveAssetUrl = useGameForgeStore((s) => s.setActiveAssetUrl);
  const setCurrentJobId = useGameForgeStore((s) => s.setCurrentJobId);
  const setErrorMessage = useGameForgeStore((s) => s.setErrorMessage);
  const setProgress = useGameForgeStore((s) => s.setProgress);

  const pollJobStatus = async (jobId: string) => {
    const maxRetries = 60;
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts++;
      try {
        const data = await getJobStatus(jobId);

        // Update real progress from backend
        setProgress(data.progress ?? 0);

        if (data.status === "COMPLETED") {
          clearInterval(interval);
          setGenerationStatus("completed");
          setProgress(100);
          if (data.asset_url) {
            setActiveAssetUrl(data.asset_url);
          }
        } else if (data.status === "FAILED") {
          clearInterval(interval);
          setGenerationStatus("failed");
          setErrorMessage(data.error || "Generation job failed.");
        }

        if (attempts >= maxRetries) {
          clearInterval(interval);
          setGenerationStatus("failed");
          setErrorMessage("Generation timed out.");
        }
      } catch (err) {
        console.error("Polling error:", err);
        if (attempts >= maxRetries) {
          clearInterval(interval);
          setGenerationStatus("failed");
          setErrorMessage("Lost connection to backend engine.");
        }
      }
    }, 500);
  };

  const handleGenerate = async (customPrompt?: string) => {
    const targetPrompt = customPrompt || prompt;
    if (!targetPrompt.trim() || generationStatus === "processing") return;

    setErrorMessage(null);
    setGenerationStatus("processing");
    setProgress(0);

    try {
      const jobData = await generateAsset(targetPrompt);
      setCurrentJobId(jobData.id);
      pollJobStatus(jobData.id);
    } catch (err) {
      console.error("Generate API call failed:", err);
      setGenerationStatus("failed");
      setErrorMessage(
        "Could not connect to the GameForge backend. Make sure the FastAPI server is running on port 8000."
      );
    }
  };

  return (
    <div className="shrink-0 border-t border-border bg-panel/70 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
          className="flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-3 py-2 focus-within:border-gold/40"
        >
          <Sparkles className="size-4 text-gold" />
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder='Describe what you want to create (e.g. "Create a red metallic cube")...'
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            disabled={generationStatus === "processing" || !prompt.trim()}
            className="inline-flex items-center gap-2 rounded-md border border-gold/40 bg-gold/15 px-4 py-1.5 text-sm text-gold transition-colors hover:bg-gold/25 disabled:opacity-50"
          >
            {generationStatus === "processing" ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                Forging...
              </>
            ) : (
              "Generate"
            )}
          </button>
        </form>

        <div className="flex flex-wrap gap-2">
          {quickActions.map(({ label, prompt: qPrompt, icon: Icon }) => (
            <button
              key={label}
              onClick={() => {
                setPrompt(qPrompt);
                handleGenerate(qPrompt);
              }}
              disabled={generationStatus === "processing"}
              className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-gold/30 hover:text-foreground disabled:opacity-50"
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
