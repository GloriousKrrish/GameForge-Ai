import { useState, useEffect } from "react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { updateObjectTransform, updateSceneObject, parentSceneObject, unparentSceneObject } from "@/api/scene";

export function PropertiesPanel() {
  const {
    selectedObjectId,
    sceneObjects,
    setSceneObjects,
    selectedObject,
    setSelectedObject,
    setActiveAssetUrl,
    setErrorMessage,
  } = useGameForgeStore();

  const [isUpdating, setIsUpdating] = useState(false);
  const [objectName, setObjectName] = useState(selectedObject?.name || "GameForge_Cube");

  const currentObj = sceneObjects.find((o) => o.id === selectedObjectId) || sceneObjects[0];

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
    </aside>
  );
}
