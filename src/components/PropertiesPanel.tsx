import { useState, useEffect } from "react";
import { User, Bone, Activity, CheckCircle2, Loader2 } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { updateObjectTransform, updateSceneObject, parentSceneObject, unparentSceneObject } from "@/api/scene";
import { rigCharacter } from "@/api/characters";
import { AnimationPlaybackControls } from "@/components/AnimationPlaybackControls";

export function PropertiesPanel() {
  const {
    selectedObjectId,
    sceneObjects,
    setSceneObjects,
    selectedObject,
    setSelectedObject,
    setActiveAssetUrl,
    setErrorMessage,
    selectedCharacter,
    setSelectedCharacter,
    setActiveSkeleton,
    isRigVisualized,
    setIsRigVisualized,
    charactersList,
    setCharactersList,
  } = useGameForgeStore();

  const [isUpdating, setIsUpdating] = useState(false);
  const [isRigging, setIsRigging] = useState(false);
  const [objectName, setObjectName] = useState(selectedObject?.name || "GameForge_Cube");

  const currentObj = sceneObjects.find((o) => o.id === selectedObjectId) || sceneObjects[0];

  const refreshCharacters = async () => {
    try {
      const { listCharacters } = await import("@/api/characters");
      const chars = await listCharacters();
      setCharactersList(chars);
    } catch (_err) { /* noop */ }
  };

  const handleRigCharacter = async () => {
    if (!selectedCharacter) return;
    setIsRigging(true);
    try {
      const res = await rigCharacter(selectedCharacter.id, { rig_type: "HUMANOID" });
      if (res.character) {
        setSelectedCharacter(res.character);
      }
      if (res.skeleton) {
        setActiveSkeleton(res.skeleton);
        setIsRigVisualized(true);
      }
      await refreshCharacters();
    } catch (err: any) {
      setErrorMessage(err.message || "Rigging failed.");
    } finally {
      setIsRigging(false);
    }
  };

  useEffect(() => {
    if (currentObj) {
      setObjectName(currentObj.name);
    }
  }, [currentObj]);


  const handleNameBlur = async () => {
    if (!currentObj || objectName === currentObj.name) return;
    setIsUpdating(true);
    try {
      const res = await updateSceneObject(currentObj.id, { name: objectName });
      if (res.success && res.scene) {
        const mapped = res.scene.objects.map((o) => ({
          id: o.id,
          name: o.name,
          type: o.object_type,
          position: o.transform.position,
          rotation: o.transform.rotation,
          scale: o.transform.scale,
          parent_id: o.parent_id,
          visible: o.visible ?? true,
        }));
        setSceneObjects(mapped);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to rename object.");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleParentChange = async (newParentId: string) => {
    if (!currentObj) return;
    setIsUpdating(true);
    try {
      let res;
      if (newParentId === "none") {
        res = await unparentSceneObject(currentObj.id);
      } else {
        res = await parentSceneObject(currentObj.id, newParentId);
      }
      if (res.success && res.scene) {
        const mapped = res.scene.objects.map((o) => ({
          id: o.id,
          name: o.name,
          type: o.object_type,
          position: o.transform.position,
          rotation: o.transform.rotation,
          scale: o.transform.scale,
          parent_id: o.parent_id,
          visible: o.visible ?? true,
        }));
        setSceneObjects(mapped);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to update parent relationship.");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleTransformChange = async (
    type: "position" | "rotation" | "scale",
    axisIndex: number,
    value: number
  ) => {
    if (!selectedObject && !currentObj) return;

    const currentValues = [...((selectedObject && selectedObject[type]) || (currentObj && currentObj[type]) || [0,0,0])] as [number, number, number];
    currentValues[axisIndex] = value;

    const updatedObj = {
      name: objectName,
      position: type === "position" ? currentValues : currentObj?.position || [0,0,0],
      rotation: type === "rotation" ? currentValues : currentObj?.rotation || [0,0,0],
      scale: type === "scale" ? currentValues : currentObj?.scale || [1,1,1],
    };
    setSelectedObject(updatedObj);

    setIsUpdating(true);
    try {
      const res = await updateObjectTransform(currentObj?.name || objectName, {
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
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="w-full">
          <h3 className="font-serif text-lg text-foreground mb-1">Properties</h3>
          <input
            type="text"
            value={objectName}
            onChange={(e) => setObjectName(e.target.value)}
            onBlur={handleNameBlur}
            onKeyDown={(e) => e.key === "Enter" && handleNameBlur()}
            className="w-full rounded border border-border bg-secondary/80 px-2 py-1 text-xs font-mono text-gold focus:border-gold focus:outline-none"
            placeholder="Object Name"
          />
        </div>
        {isUpdating && <span className="ml-2 text-[10px] text-amber-400 animate-pulse shrink-0">Syncing...</span>}
      </div>

      {/* Parent Hierarchy Selection */}
      <section className="space-y-2">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft">Hierarchy Parent</p>
        <select
          value={currentObj?.parent_id || "none"}
          onChange={(e) => handleParentChange(e.target.value)}
          className="w-full rounded border border-border bg-secondary/80 px-2 py-1.5 text-xs text-foreground focus:border-gold focus:outline-none"
        >
          <option value="none">None (Root Level)</option>
          {sceneObjects
            .filter((o) => o.id !== currentObj?.id)
            .map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} ({o.type})
              </option>
            ))}
        </select>
      </section>

      {/* Transform */}
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
                  value={currentObj?.position[i] ?? 0}
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
                  value={currentObj?.rotation[i] ?? 0}
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
                  value={currentObj?.scale[i] ?? 1}
                  onChange={(e) => handleTransformChange("scale", i, parseFloat(e.target.value) || 1)}
                  className="w-full bg-transparent text-xs text-foreground focus:outline-none"
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Material (Phase 3B PBR Controls) */}
      <section className="space-y-3">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft">Material (PBR Engine)</p>

        {/* Preset Selector */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-muted-foreground">Quick Preset</span>
          <select
            onChange={async (e) => {
              const presetId = e.target.value;
              if (!presetId || !currentObj) return;
              setIsUpdating(true);
              try {
                const { assignMaterialToObject } = await import("@/api/material");
                const { getActiveScene } = await import("@/api/scene");
                await assignMaterialToObject(currentObj.id, presetId);
                const scene = await getActiveScene();
                if (scene && scene.objects) {
                  const mapped = scene.objects.map((o: any) => ({
                    id: o.id,
                    name: o.name,
                    type: o.object_type,
                    position: o.transform.position,
                    rotation: o.transform.rotation,
                    scale: o.transform.scale,
                    parent_id: o.parent_id,
                    visible: o.visible ?? true,
                  }));
                  setSceneObjects(mapped);
                }
              } catch (err: any) {
                setErrorMessage(err.message || "Failed to apply preset.");
              } finally {
                setIsUpdating(false);
              }
            }}
            className="w-full rounded border border-border bg-secondary/80 px-2 py-1 text-xs text-foreground focus:border-gold focus:outline-none"
          >
            <option value="">-- Apply Preset --</option>
            <option value="mat_preset_matte_black">Matte Black</option>
            <option value="mat_preset_brushed_gold">Brushed Gold</option>
            <option value="mat_preset_chrome">Chrome</option>
            <option value="mat_preset_plastic">Plastic</option>
            <option value="mat_preset_rubber">Rubber</option>
            <option value="mat_preset_glass">Glass</option>
            <option value="mat_preset_gold">Gold</option>
          </select>
        </div>

        {/* Base Color Picker */}
        <div className="grid grid-cols-[70px_1fr] items-center gap-2">
          <span className="text-xs text-muted-foreground">Base Color</span>
          <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/60 px-2 py-1">
            <input
              type="color"
              defaultValue="#E8B4B8"
              onChange={async (e) => {
                const colorHex = e.target.value;
                if (!currentObj) return;
                try {
                  const res = await updateObjectTransform(currentObj.name, { color: colorHex } as any);
                  if (res.success && res.glb_url) {
                    setActiveAssetUrl(res.glb_url);
                  }
                } catch (err: any) {
                  console.error("Failed to update material color:", err);
                }
              }}
              className="size-5 rounded border border-border bg-transparent cursor-pointer"
            />
            <span className="text-xs font-mono text-foreground">Color</span>
          </div>
        </div>

        {/* Metallic & Roughness sliders */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Metallic</span>
            <span className="text-[10px] font-mono text-gold-soft">PBR</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            defaultValue="0.4"
            className="w-full accent-gold cursor-pointer"
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Roughness</span>
            <span className="text-[10px] font-mono text-gold-soft">PBR</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            defaultValue="0.5"
            className="w-full accent-gold cursor-pointer"
          />
        </div>
      </section>

      {/* ---- Character Inspector (Phase 5) ---- */}
      {selectedCharacter && (
        <section className="space-y-3 border-t border-border pt-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft">Character Inspector</p>

          {/* Character Name + Status */}
          <div className="rounded-lg border border-gold/20 bg-gold/5 p-2.5 flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <User className="size-4 text-gold shrink-0" />
              <span className="font-semibold text-xs text-foreground truncate">{selectedCharacter.name}</span>
            </div>
            <span className="font-mono text-[10px] text-muted-foreground truncate">{selectedCharacter.id}</span>

            {/* Status Badge */}
            <div className="flex items-center gap-1.5 mt-0.5">
              {selectedCharacter.status === "READY" ? (
                <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="size-3" /> READY · Animation-Ready
                </span>
              ) : selectedCharacter.status === "RIGGED" ? (
                <span className="inline-flex items-center gap-1 rounded bg-blue-500/15 px-2 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/30">
                  <Bone className="size-3" /> RIGGED · Deterministic
                </span>
              ) : selectedCharacter.status === "RIGGING" || isRigging ? (
                <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-400 border border-amber-500/30 animate-pulse">
                  <Loader2 className="size-3 animate-spin" /> RIGGING…
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {selectedCharacter.status}
                </span>
              )}
            </div>
          </div>

          {/* Character Meta Fields */}
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="rounded-md border border-border bg-secondary/40 px-2 py-1.5">
              <span className="block text-[10px] text-muted-foreground mb-0.5">Type</span>
              <span className="font-semibold text-foreground">{selectedCharacter.character_type}</span>
            </div>
            <div className="rounded-md border border-border bg-secondary/40 px-2 py-1.5">
              <span className="block text-[10px] text-muted-foreground mb-0.5">Rig ID</span>
              <span className="font-mono text-[10px] text-gold-soft truncate block">
                {selectedCharacter.rig_id ?? "—"}
              </span>
            </div>
            {selectedCharacter.skinning && (
              <>
                <div className="rounded-md border border-border bg-secondary/40 px-2 py-1.5">
                  <span className="block text-[10px] text-muted-foreground mb-0.5">Vertices</span>
                  <span className="font-semibold text-foreground">{selectedCharacter.skinning.vertex_count}</span>
                </div>
                <div className="rounded-md border border-border bg-secondary/40 px-2 py-1.5">
                  <span className="block text-[10px] text-muted-foreground mb-0.5">Max Infl.</span>
                  <span className="font-semibold text-foreground">{selectedCharacter.skinning.max_influences_per_vertex}</span>
                </div>
              </>
            )}
          </div>

          {/* Skinning Status */}
          {selectedCharacter.skinning && (
            <div className="flex items-center justify-between rounded-md border border-border bg-secondary/30 px-2.5 py-1.5 text-[11px]">
              <span className="text-muted-foreground">Skinning Status</span>
              <span className={`font-semibold ${
                selectedCharacter.skinning.status === "VALID" ? "text-emerald-400"
                : selectedCharacter.skinning.status === "NOT_AVAILABLE" ? "text-amber-400"
                : "text-red-400"
              }`}>
                {selectedCharacter.skinning.status}
              </span>
            </div>
          )}

          {/* Character Actions */}
          <div className="flex gap-1.5">
            <button
              onClick={handleRigCharacter}
              disabled={isRigging || selectedCharacter.status === "RIGGING"}
              id="btn-rig-character-props"
              className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-gold px-3 py-1.5 text-[11px] font-semibold text-background hover:bg-gold/90 disabled:opacity-50 transition-colors"
            >
              {isRigging ? <Loader2 className="size-3.5 animate-spin" /> : <Bone className="size-3.5" />}
              {isRigging ? "Rigging…" : "Rig Character"}
            </button>
            <button
              onClick={() => setIsRigVisualized(!isRigVisualized)}
              id="btn-toggle-rig-vis"
              className={`flex items-center justify-center gap-1 rounded-md border px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                isRigVisualized
                  ? "border-gold/40 bg-gold/10 text-gold"
                  : "border-border bg-secondary text-foreground hover:border-gold/30"
              }`}
              title={isRigVisualized ? "Hide Rig Overlay" : "Show Rig Overlay"}
            >
              <Activity className="size-3.5" />
            </button>
          </div>

          {/* Phase 6D-C Animation Playback Controls */}
          <AnimationPlaybackControls />
        </section>
      )}
    </aside>
  );
}
