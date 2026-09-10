import { useState } from "react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { updateObjectTransform } from "@/api/scene";

export function PropertiesPanel() {
  const { selectedObject, setSelectedObject, setActiveAssetUrl, setErrorMessage } = useGameForgeStore();
  const [isUpdating, setIsUpdating] = useState(false);

  const handleTransformChange = async (
    type: "position" | "rotation" | "scale",
    axisIndex: number,
    value: number
  ) => {
    if (!selectedObject) return;

    const currentValues = [...selectedObject[type]] as [number, number, number];
    currentValues[axisIndex] = value;

    const updatedObj = {
      ...selectedObject,
      [type]: currentValues,
    };
    setSelectedObject(updatedObj);

    // Call real backend execution
    setIsUpdating(true);
    try {
      const res = await updateObjectTransform(selectedObject.name, {
        [type]: currentValues,
      });
      if (res.success && res.glb_url) {
        setActiveAssetUrl(res.glb_url);
      }
    } catch (err: any) {
      console.error("Failed to update transform authoritatively:", err);
      setErrorMessage(err.message || "Failed to update transform on backend.");
    } finally {
      setIsUpdating(false);
    }
  };

  const axes = ["X", "Y", "Z"];

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-6 overflow-y-auto border-l border-border bg-panel/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-serif text-lg text-foreground">Properties</h3>
          <p className="text-xs font-mono text-gold-soft">{selectedObject?.name || "GameForge_Cube"}</p>
        </div>
        {isUpdating && <span className="text-[10px] text-amber-400 animate-pulse">Syncing...</span>}
      </div>

      <section className="space-y-3">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft">Transform (Authoritative)</p>

        {/* Position */}
        <div className="grid grid-cols-[64px_1fr] items-center gap-2">
          <span className="text-xs text-muted-foreground">Position</span>
          <div className="grid grid-cols-3 gap-1.5">
            {axes.map((axis, i) => (
              <div key={`pos-${axis}`} className="flex items-center gap-1 rounded-md border border-border bg-secondary/60 px-1.5 py-1">
                <span className="text-[10px] text-gold-soft">{axis}</span>
                <input
                  type="number"
                  step="0.5"
                  value={selectedObject?.position[i] ?? 0}
                  onChange={(e) => handleTransformChange("position", i, parseFloat(e.target.value) || 0)}
                  className="w-full bg-transparent text-xs text-foreground focus:outline-none"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Rotation */}
        <div className="grid grid-cols-[64px_1fr] items-center gap-2">
          <span className="text-xs text-muted-foreground">Rotation</span>
          <div className="grid grid-cols-3 gap-1.5">
            {axes.map((axis, i) => (
              <div key={`rot-${axis}`} className="flex items-center gap-1 rounded-md border border-border bg-secondary/60 px-1.5 py-1">
                <span className="text-[10px] text-gold-soft">{axis}</span>
                <input
                  type="number"
                  step="15"
                  value={selectedObject?.rotation[i] ?? 0}
                  onChange={(e) => handleTransformChange("rotation", i, parseFloat(e.target.value) || 0)}
                  className="w-full bg-transparent text-xs text-foreground focus:outline-none"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Scale */}
        <div className="grid grid-cols-[64px_1fr] items-center gap-2">
          <span className="text-xs text-muted-foreground">Scale</span>
          <div className="grid grid-cols-3 gap-1.5">
            {axes.map((axis, i) => (
              <div key={`scl-${axis}`} className="flex items-center gap-1 rounded-md border border-border bg-secondary/60 px-1.5 py-1">
                <span className="text-[10px] text-gold-soft">{axis}</span>
                <input
                  type="number"
                  step="0.2"
                  value={selectedObject?.scale[i] ?? 1}
                  onChange={(e) => handleTransformChange("scale", i, parseFloat(e.target.value) || 1)}
                  className="w-full bg-transparent text-xs text-foreground focus:outline-none"
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft">Material</p>
        <div className="grid grid-cols-[64px_1fr] items-center gap-2">
          <span className="text-xs text-muted-foreground">Base Color</span>
          <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/60 px-2 py-1.5">
            <span className="size-4 rounded border border-border bg-rose" />
            <span className="text-xs text-foreground">#E8B4B8</span>
          </div>
        </div>
      </section>
    </aside>
  );
}
