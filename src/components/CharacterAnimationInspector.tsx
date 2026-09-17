import { useState, useEffect } from "react";
import {
  User,
  Bone,
  Activity,
  CheckCircle2,
  Loader2,
  Search,
  Film,
  AlertCircle,
  Layers,
  Sparkles,
} from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { rigCharacter } from "@/api/characters";
import { listCharacterAnimations, type AnimationData } from "@/api/animations";
import { animationRuntime, animationClipLoader } from "@/runtime/animationRuntime";
import { AnimationPlaybackControls } from "./AnimationPlaybackControls";

export function CharacterAnimationInspector() {
  const {
    selectedCharacter,
    setSelectedCharacter,
    activeSkeleton,
    setActiveSkeleton,
    isRigVisualized,
    setIsRigVisualized,
    setCharactersList,
    setErrorMessage,
    activeAnimationId,
    setActiveAnimationId,
    isPlaying,
    setIsPlaying,
    playbackSpeed,
    loopMode,
    isAnimationLoading,
    setIsAnimationLoading,
    animationError,
    setAnimationError,
  } = useGameForgeStore();

  const [isRigging, setIsRigging] = useState(false);
  const [animations, setAnimations] = useState<AnimationData[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isFetchingList, setIsFetchingList] = useState(false);

  const characterId = selectedCharacter?.id;

  // 1. Fetch character animations when selected character changes
  useEffect(() => {
    if (!characterId) {
      setAnimations([]);
      setSearchQuery("");
      setActiveAnimationId(null);
      setIsPlaying(false);
      setAnimationError(null);
      return;
    }

    setSearchQuery("");
    setActiveAnimationId(null);
    setIsPlaying(false);
    setAnimationError(null);
    setIsFetchingList(true);

    let isSubscribed = true;

    listCharacterAnimations(characterId)
      .then((data) => {
        if (!isSubscribed) return;
        setAnimations(data || []);
        setIsFetchingList(false);
      })
      .catch((err) => {
        if (!isSubscribed) return;
        console.error("Failed to list character animations:", err);
        setAnimations([]);
        setIsFetchingList(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [characterId, setActiveAnimationId, setIsPlaying, setAnimationError]);

  if (!selectedCharacter) {
    return null;
  }

  const refreshCharacters = async () => {
    try {
      const { listCharacters } = await import("@/api/characters");
      const chars = await listCharacters();
      setCharactersList(chars);
    } catch (_err) {
      /* noop */
    }
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

  // Select Animation Clip from List
  const handleSelectAnimation = async (animData: AnimationData) => {
    if (!characterId) return;

    if (animData.status !== "READY") {
      setAnimationError(`Animation "${animData.name}" is ${animData.status.toLowerCase()} and cannot be played.`);
      return;
    }

    if (activeAnimationId === animData.id) return;

    setIsAnimationLoading(true);
    setAnimationError(null);

    try {
      if (!animationRuntime.hasAnimationClip(characterId, animData.id)) {
        await animationClipLoader.loadAndBindClip(characterId, animData, animationRuntime);
      }
      setActiveAnimationId(animData.id);
    } catch (err: any) {
      console.error("Failed to load/bind clip:", err);
      setAnimationError(err.message || "Unable to load animation clip.");
      setActiveAnimationId(null);
    } finally {
      setIsAnimationLoading(false);
    }
  };

  // Filter animations by search query
  const filteredAnimations = animations.filter((a) =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.animation_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedAnimData = animations.find((a) => a.id === activeAnimationId);

  // Derived Skeleton Stats
  const boneCount = activeSkeleton?.bone_count || activeSkeleton?.bones?.length || 0;
  const rootBoneName = activeSkeleton?.root_bone_id || activeSkeleton?.bones?.[0]?.name || "—";

  return (
    <section className="space-y-4 border-t border-border pt-3">
      {/* ── 1. Character & Rig / Skeleton Overview Header ── */}
      <div className="space-y-2">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft flex items-center justify-between">
          <span>Character Inspector</span>
          <span className="font-mono text-[9px] text-muted-foreground">{selectedCharacter.id}</span>
        </p>

        {/* Character Card */}
        <div className="rounded-lg border border-gold/25 bg-gold/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <User className="size-4 text-gold shrink-0" />
              <span className="font-semibold text-xs text-foreground truncate">{selectedCharacter.name}</span>
            </div>
            {/* Character Status Badge */}
            {selectedCharacter.status === "READY" ? (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/30">
                <CheckCircle2 className="size-3" /> READY
              </span>
            ) : selectedCharacter.status === "RIGGED" ? (
              <span className="inline-flex items-center gap-1 rounded bg-blue-500/15 px-2 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/30">
                <Bone className="size-3" /> RIGGED
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

          {/* Character & Skeleton Meta Grid */}
          <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono pt-1">
            <div className="rounded bg-secondary/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">TYPE</span>
              <span className="font-semibold text-foreground">{selectedCharacter.character_type}</span>
            </div>
            <div className="rounded bg-secondary/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">RIG ID</span>
              <span className="font-semibold text-gold-soft truncate block">{selectedCharacter.rig_id || "—"}</span>
            </div>
            <div className="rounded bg-secondary/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">BONES</span>
              <span className="font-semibold text-foreground">{boneCount > 0 ? `${boneCount} bones` : "—"}</span>
            </div>
            <div className="rounded bg-secondary/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">ROOT BONE</span>
              <span className="font-semibold text-gold-soft truncate block">{rootBoneName}</span>
            </div>
          </div>

          {/* Skinning Status Info */}
          {selectedCharacter.skinning && (
            <div className="flex items-center justify-between rounded bg-secondary/30 px-2 py-1 text-[10px] border border-border">
              <span className="text-muted-foreground">Skinning Vertices</span>
              <span className="font-semibold text-foreground font-mono">
                {selectedCharacter.skinning.vertex_count} ({selectedCharacter.skinning.status})
              </span>
            </div>
          )}

          {/* Rig Action Buttons */}
          <div className="flex gap-1.5 pt-1">
            <button
              onClick={handleRigCharacter}
              disabled={isRigging || selectedCharacter.status === "RIGGING"}
              id="btn-rig-character-inspector"
              className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-gold px-3 py-1.5 text-[11px] font-semibold text-background hover:bg-gold/90 disabled:opacity-50 transition-colors"
            >
              {isRigging ? <Loader2 className="size-3.5 animate-spin" /> : <Bone className="size-3.5" />}
              {isRigging ? "Rigging…" : "Rig Character"}
            </button>
            <button
              onClick={() => setIsRigVisualized(!isRigVisualized)}
              id="btn-toggle-rig-vis-inspector"
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
        </div>
      </div>

      {/* ── 2. Animation List & Local Search Section ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft flex items-center gap-1">
            <Film className="size-3 text-gold shrink-0" />
            Animations ({animations.length})
          </p>
          {isFetchingList && <Loader2 className="size-3 animate-spin text-gold" />}
        </div>

        {/* Local Search Input */}
        {animations.length > 0 && (
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 size-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search animations…"
              className="w-full rounded border border-border bg-secondary/80 pl-8 pr-2 py-1 text-xs text-foreground focus:border-gold focus:outline-none placeholder:text-muted-foreground/60"
              id="input-search-animations"
            />
          </div>
        )}

        {/* Animation List */}
        {isFetchingList ? (
          <div className="flex items-center gap-2 rounded border border-border bg-secondary/40 p-3 text-xs text-muted-foreground justify-center">
            <Loader2 className="size-3.5 animate-spin text-gold" />
            Loading character animations…
          </div>
        ) : filteredAnimations.length === 0 ? (
          <div className="rounded border border-border bg-secondary/30 p-3 text-xs text-muted-foreground text-center">
            {searchQuery ? `No animations matching "${searchQuery}"` : "This character does not have any animations yet."}
          </div>
        ) : (
          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-0.5">
            {filteredAnimations.map((anim) => {
              const isSelected = activeAnimationId === anim.id;
              const isReady = anim.status === "READY";

              return (
                <div
                  key={anim.id}
                  onClick={() => handleSelectAnimation(anim)}
                  className={`rounded-md border p-2 text-xs transition-all cursor-pointer ${
                    isSelected
                      ? "border-gold bg-gold/10 text-foreground shadow-sm"
                      : isReady
                      ? "border-border bg-secondary/40 hover:border-gold/30 text-muted-foreground hover:text-foreground"
                      : "border-border/50 bg-secondary/20 text-muted-foreground/60 cursor-not-allowed"
                  }`}
                  id={`anim-item-${anim.id}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${isSelected ? "text-gold" : "text-muted-foreground"}`}>
                        {isSelected ? "●" : "○"}
                      </span>
                      <span className="font-semibold text-xs text-foreground">{anim.name}</span>
                    </div>

                    {/* Status Badge */}
                    <span
                      className={`text-[9px] font-semibold font-mono rounded px-1.5 py-0.5 border ${
                        anim.status === "READY"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : anim.status === "GENERATING"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse"
                          : "bg-red-500/10 text-red-400 border-red-500/20"
                      }`}
                    >
                      {anim.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground mt-1 pl-4">
                    <span>{anim.animation_type}</span>
                    <span>{anim.duration_seconds}s · {anim.fps || 30} FPS</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 3. Selected Animation Metadata Details Card ── */}
      {selectedAnimData && (
        <div className="space-y-1.5 rounded-lg border border-border bg-secondary/40 p-2.5">
          <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft flex items-center justify-between">
            <span>Selected Animation</span>
            <span className="font-mono text-[9px] text-gold">{selectedAnimData.id}</span>
          </p>

          <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">NAME</span>
              <span className="font-semibold text-foreground truncate block">{selectedAnimData.name}</span>
            </div>
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">TYPE</span>
              <span className="font-semibold text-gold truncate block">{selectedAnimData.animation_type}</span>
            </div>
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">DURATION</span>
              <span className="font-semibold text-foreground">{selectedAnimData.duration_seconds}s</span>
            </div>
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">FPS / FRAMES</span>
              <span className="font-semibold text-foreground">
                {selectedAnimData.fps || 30} FPS (1–{Math.round(selectedAnimData.duration_seconds * (selectedAnimData.fps || 30))})
              </span>
            </div>
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">LOOP MODE</span>
              <span className="font-semibold text-foreground">{loopMode}</span>
            </div>
            <div className="rounded bg-background/50 px-2 py-1 border border-border">
              <span className="block text-[9px] text-muted-foreground">PLAYBACK</span>
              <span className={`font-semibold ${isPlaying ? "text-emerald-400" : "text-amber-400"}`}>
                {isPlaying ? "Playing" : "Stopped / Paused"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── 4. Composed Playback Controls & Timeline ── */}
      <AnimationPlaybackControls />
    </section>
  );
}
