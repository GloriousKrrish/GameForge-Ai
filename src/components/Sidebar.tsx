import { useState, useEffect } from "react";
import { Boxes, Box, Layers, Eye, EyeOff, Trash2 } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { getActiveScene, updateSceneObject, deleteSceneObject } from "@/api/scene";

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<"hierarchy" | "assets">("hierarchy");
  const {
    sceneObjects,
    setSceneObjects,
    selectedObjectId,
    setSelectedObjectId,
    setSelectedObject,
    setErrorMessage,
  } = useGameForgeStore();

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
        }
      } catch (err: any) {
        console.error("Failed to load active scene:", err);
      }
    }
    loadScene();
  }, [setSceneObjects]);

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

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-panel/60 p-3">
      {/* Tabs Header */}
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
          Assets
        </button>
      </div>

      {activeTab === "hierarchy" ? (
        <div className="mt-3 flex flex-col gap-1 overflow-y-auto">
          <p className="px-2 text-[10px] uppercase tracking-[0.2em] text-muted-foreground pb-1">
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
        <div className="mt-3 rounded-md border border-border p-3 text-xs text-muted-foreground">
          <p className="text-foreground">Assets Library</p>
          <p className="mt-1 leading-relaxed">
            Generated mesh GLB models will be listed here.
          </p>
        </div>
      )}
    </aside>
  );
}
