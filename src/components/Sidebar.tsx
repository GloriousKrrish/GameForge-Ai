import { useState, useEffect } from "react";
import { Boxes, Box, Layers, Eye, EyeOff, Trash2, Sparkles, Plus, Loader2, Palette, Cpu, AlertTriangle } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { getActiveScene, updateSceneObject, deleteSceneObject } from "@/api/scene";
import { listMaterials, assignMaterialToObject } from "@/api/material";
import { listAssets, generateAsset3D, instantiateAssetInScene, deleteAsset, AssetModelData } from "@/api/asset";

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<"hierarchy" | "assets">("hierarchy");
  const [assetSubTab, setAssetSubTab] = useState<"models" | "materials">("models");

  // Asset Generation Form State
  const [genPrompt, setGenPrompt] = useState("");
  const [genStyle, setGenStyle] = useState<"realistic" | "stylized" | "low-poly">("realistic");
  const [genQuality, setGenQuality] = useState<"draft" | "standard" | "high">("standard");
  const [genTargetUse, setGenTargetUse] = useState<"game_asset" | "render" | "background">("game_asset");
  const [isGenerating, setIsGenerating] = useState(false);
  const [genStatusMsg, setGenStatusMsg] = useState<string | null>(null);

  const {
    sceneObjects,
    setSceneObjects,
    selectedObjectId,
    setSelectedObjectId,
    setSelectedObject,
    setErrorMessage,
    materialsList,
    setMaterialsList,
    assetsList,
    setAssetsList,
    setActiveAssetUrl,
  } = useGameForgeStore();

  const refreshAssets = async () => {
    try {
      const assets = await listAssets();
      setAssetsList(assets);
    } catch (err: any) {
      console.error("Failed to load assets list:", err);
    }
  };

  useEffect(() => {
    async function loadScene() {
      try {
        const scene = await getActiveScene();
        if (scene && scene.objects) {
          const mapped = scene.objects.map((o) => ({
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
          if (scene.active_asset_url) {
            setActiveAssetUrl(scene.active_asset_url);
          }
        }
      } catch (err: any) {
        console.error("Failed to load active scene:", err);
      }
    }

    async function loadMaterials() {
      try {
        const mats = await listMaterials();
        setMaterialsList(mats);
      } catch (err: any) {
        console.error("Failed to load materials list:", err);
      }
    }

    loadScene();
    loadMaterials();
    refreshAssets();
  }, [setSceneObjects, setMaterialsList, setAssetsList, setActiveAssetUrl]);

  const handleSelect = (obj: any) => {
    setSelectedObjectId(obj.id);
    setSelectedObject({
      name: obj.name,
      position: obj.position,
      rotation: obj.rotation,
      scale: obj.scale,
    });
  };

  const handleToggleVisibility = async (e: React.MouseEvent, obj: any) => {
    e.stopPropagation();
    const newVis = !obj.visible;
    try {
      const res = await updateSceneObject(obj.id, { visible: newVis });
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
      setErrorMessage(err.message || "Failed to update object visibility.");
    }
  };

  const handleDelete = async (e: React.MouseEvent, objId: string) => {
    e.stopPropagation();
    try {
      const res = await deleteSceneObject(objId);
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
        if (selectedObjectId === objId) {
          setSelectedObjectId(mapped[0]?.id || null);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to delete object.");
    }
  };

  const handleGenerateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!genPrompt.trim()) return;

    setIsGenerating(true);
    setGenStatusMsg("Generating 3D Asset pipeline active...");
    try {
      const newAsset = await generateAsset3D({
        prompt: genPrompt.trim(),
        style: genStyle,
        quality: genQuality,
        target_use: genTargetUse,
        generate_materials: true,
      });
      setGenStatusMsg(`Asset created successfully: ${newAsset.name}`);
      setGenPrompt("");
      await refreshAssets();
    } catch (err: any) {
      console.error("Asset generation error:", err);
      setErrorMessage(err.message || "3D Asset Generation failed.");
      setGenStatusMsg("Generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleInstantiateAsset = async (assetId: string) => {
    try {
      const res = await instantiateAssetInScene(assetId);
      if (res.success && res.scene) {
        const mapped = res.scene.objects.map((o: any) => ({
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
        if (res.glb_url) {
          setActiveAssetUrl(res.glb_url);
        }
        if (res.instantiated_object) {
          setSelectedObjectId(res.instantiated_object.id);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to instantiate asset into scene.");
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    try {
      await deleteAsset(assetId);
      await refreshAssets();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to delete asset.");
    }
  };

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-border bg-panel/60 p-3 overflow-hidden">
      {/* Primary Tabs Header */}
      <div className="flex border-b border-border pb-2 gap-1">
        <button
          onClick={() => setActiveTab("hierarchy")}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
            activeTab === "hierarchy" ? "bg-gold/15 text-gold" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
          }`}
        >
          <Layers className="size-3.5" />
          Hierarchy ({sceneObjects.length})
        </button>
        <button
          onClick={() => setActiveTab("assets")}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
            activeTab === "assets" ? "bg-gold/15 text-gold" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
          }`}
        >
          <Boxes className="size-3.5" />
          Asset Library
        </button>
      </div>

      {activeTab === "hierarchy" ? (
        <div className="mt-3 flex flex-col gap-1 overflow-y-auto pr-1">
          <p className="px-2 text-[10px] uppercase tracking-[0.2em] text-muted-foreground pb-1 font-semibold">
            Scene Objects
          </p>
          {sceneObjects.length === 0 ? (
            <p className="px-2 text-xs text-muted-foreground">Scene is empty</p>
          ) : (
            sceneObjects.map((obj) => {
              const isSelected = selectedObjectId === obj.id;
              const isChild = !!obj.parent_id;

              return (
                <div
                  key={obj.id}
                  onClick={() => handleSelect(obj)}
                  className={`group flex items-center justify-between rounded-md border px-2.5 py-1.5 text-xs transition-colors cursor-pointer ${
                    isChild ? "ml-4 border-dashed" : ""
                  } ${
                    isSelected
                      ? "border-gold/40 bg-gold/10 text-gold font-medium"
                      : "border-transparent text-muted-foreground hover:border-border hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <Box className="size-3.5 shrink-0 text-gold-soft" />
                    <span className="truncate">{obj.name}</span>
                  </div>

                  <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                    <button
                      onClick={(e) => handleToggleVisibility(e, obj)}
                      title={obj.visible ? "Hide object" : "Show object"}
                      className="p-1 hover:text-foreground text-muted-foreground"
                    >
                      {obj.visible !== false ? (
                        <Eye className="size-3 text-gold-soft" />
                      ) : (
                        <EyeOff className="size-3 text-muted-foreground" />
                      )}
                    </button>
                    <button
                      onClick={(e) => handleDelete(e, obj.id)}
                      title="Delete object"
                      className="p-1 hover:text-red-400 text-muted-foreground"
                    >
                      <Trash2 className="size-3" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-3 overflow-y-auto pr-1">
          {/* Secondary Sub-Tabs for Asset Browser */}
          <div className="flex rounded bg-secondary/50 p-0.5 text-xs">
            <button
              onClick={() => setAssetSubTab("models")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1 rounded font-medium transition-colors ${
                assetSubTab === "models" ? "bg-panel text-gold shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Cpu className="size-3" />
              3D Assets ({assetsList.length})
            </button>
            <button
              onClick={() => setAssetSubTab("materials")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1 rounded font-medium transition-colors ${
                assetSubTab === "materials" ? "bg-panel text-gold shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Palette className="size-3" />
              Materials ({materialsList.length})
            </button>
          </div>

          {assetSubTab === "models" ? (
            <div className="flex flex-col gap-3">
              {/* Asset Generation Form */}
              <form onSubmit={handleGenerateAsset} className="rounded-lg border border-gold/30 bg-gold/5 p-3 flex flex-col gap-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-gold">
                  <Sparkles className="size-3.5" />
                  AI 3D Asset Generator
                </div>

                <input
                  type="text"
                  placeholder="Describe asset (e.g. futuristic sports car)..."
                  value={genPrompt}
                  onChange={(e) => setGenPrompt(e.target.value)}
                  disabled={isGenerating}
                  className="w-full rounded border border-border bg-background px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-gold focus:outline-none"
                />

                <div className="grid grid-cols-3 gap-1.5 text-[11px]">
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-0.5">Style</label>
                    <select
                      value={genStyle}
                      onChange={(e: any) => setGenStyle(e.target.value)}
                      className="w-full rounded border border-border bg-background px-1 py-1 text-xs text-foreground"
                    >
                      <option value="realistic">Realistic</option>
                      <option value="stylized">Stylized</option>
                      <option value="low-poly">Low-Poly</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-0.5">Quality</label>
                    <select
                      value={genQuality}
                      onChange={(e: any) => setGenQuality(e.target.value)}
                      className="w-full rounded border border-border bg-background px-1 py-1 text-xs text-foreground"
                    >
                      <option value="draft">Draft</option>
                      <option value="standard">Standard</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground block mb-0.5">Use</label>
                    <select
                      value={genTargetUse}
                      onChange={(e: any) => setGenTargetUse(e.target.value)}
                      className="w-full rounded border border-border bg-background px-1 py-1 text-xs text-foreground"
                    >
                      <option value="game_asset">Game Asset</option>
                      <option value="render">Render</option>
                      <option value="background">Background</option>
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isGenerating || !genPrompt.trim()}
                  className="mt-1 flex items-center justify-center gap-1.5 rounded bg-gold px-3 py-1.5 text-xs font-semibold text-background hover:bg-gold/90 disabled:opacity-50 transition-colors"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-3.5" />
                      Generate 3D Asset
                    </>
                  )}
                </button>

                {genStatusMsg && (
                  <p className="text-[10px] text-gold-soft italic text-center">{genStatusMsg}</p>
                )}
              </form>

              {/* Registered 3D Assets Browser */}
              <div className="flex flex-col gap-2">
                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-semibold">
                  Registered Assets ({assetsList.length})
                </p>

                {assetsList.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic px-1">No 3D assets registered yet.</p>
                ) : (
                  assetsList.map((asset: AssetModelData) => {
                    const isFallback = asset.provider === "deterministic_fallback";

                    return (
                      <div
                        key={asset.id}
                        className="rounded-lg border border-border/80 bg-secondary/20 p-2.5 flex flex-col gap-1.5 transition-colors hover:border-gold/30"
                      >
                        <div className="flex items-start justify-between gap-1">
                          <div className="flex flex-col truncate">
                            <span className="font-medium text-xs text-foreground truncate">{asset.name}</span>
                            <span className="text-[10px] text-muted-foreground truncate">{asset.id}</span>
                          </div>
                          <button
                            onClick={() => handleDeleteAsset(asset.id)}
                            title="Delete Asset"
                            className="text-muted-foreground hover:text-red-400 p-0.5"
                          >
                            <Trash2 className="size-3" />
                          </button>
                        </div>

                        {/* Provider Provenance Badge */}
                        <div>
                          {isFallback ? (
                            <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-semibold text-amber-400 border border-amber-500/30">
                              <AlertTriangle className="size-2.5" />
                              DETERMINISTIC / PROCEDURAL FALLBACK
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-400 border border-emerald-500/30">
                              <Cpu className="size-2.5" />
                              AI Provider: {asset.provider}
                            </span>
                          )}
                        </div>

                        {/* Details */}
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <span>Tris: {asset.triangle_count ?? 0}</span>
                          <span>Format: {asset.format.toUpperCase()}</span>
                          <span className="uppercase text-gold-soft font-semibold">{asset.status}</span>
                        </div>

                        {/* Instantiate Action Button */}
                        <button
                          onClick={() => handleInstantiateAsset(asset.id)}
                          className="mt-0.5 flex items-center justify-center gap-1.5 rounded bg-gold/15 border border-gold/30 py-1 text-xs font-semibold text-gold hover:bg-gold/30 transition-colors"
                        >
                          <Plus className="size-3" />
                          Add to Scene
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="px-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground pb-1 font-semibold">
                Materials & Presets
              </p>
              {materialsList.length === 0 ? (
                <p className="px-1 text-xs text-muted-foreground">No materials found</p>
              ) : (
                materialsList.map((mat) => {
                  const r = Math.round((mat.base_color?.[0] ?? 0.9) * 255);
                  const g = Math.round((mat.base_color?.[1] ?? 0.9) * 255);
                  const b = Math.round((mat.base_color?.[2] ?? 0.9) * 255);
                  const colorStyle = `rgb(${r}, ${g}, ${b})`;

                  return (
                    <div
                      key={mat.id}
                      className="flex items-center justify-between rounded-md border border-border/60 bg-secondary/30 p-2 text-xs transition-colors hover:border-gold/30"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <span
                          className="size-4 shrink-0 rounded-full border border-white/20 shadow-sm"
                          style={{ backgroundColor: colorStyle }}
                        />
                        <div className="flex flex-col truncate">
                          <span className="font-medium text-foreground truncate">{mat.name}</span>
                          <span className="text-[10px] text-muted-foreground">
                            Met: {mat.metallic?.toFixed(1)} · Rgh: {mat.roughness?.toFixed(1)}
                          </span>
                        </div>
                      </div>

                      {selectedObjectId && (
                        <button
                          onClick={async () => {
                            try {
                              await assignMaterialToObject(selectedObjectId, mat.id);
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
                              setErrorMessage(err.message || "Failed to assign material.");
                            }
                          }}
                          className="rounded bg-gold/15 px-2 py-0.5 text-[10px] font-medium text-gold hover:bg-gold/30 transition-colors"
                        >
                          Assign
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
