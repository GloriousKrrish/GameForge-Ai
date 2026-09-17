import { useState, useEffect } from "react";
import * as THREE from "three";
import { Play, Pause, Square, Film, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { listCharacterAnimations, type AnimationData } from "@/api/animations";
import { animationRuntime, animationClipLoader } from "@/runtime/animationRuntime";

export function AnimationPlaybackControls() {
  const {
    selectedCharacter,
    activeAnimationId,
    setActiveAnimationId,
    isPlaying,
    setIsPlaying,
    playbackSpeed,
    setPlaybackSpeed,
    loopMode,
    setLoopMode,
    isAnimationLoading,
    setIsAnimationLoading,
    animationError,
    setAnimationError,
  } = useGameForgeStore();

  const [animations, setAnimations] = useState<AnimationData[]>([]);
  const [isFetchingList, setIsFetchingList] = useState(false);

  const characterId = selectedCharacter?.id;

  // 1. Fetch character animations when selected character changes
  useEffect(() => {
    if (!characterId) {
      setAnimations([]);
      setActiveAnimationId(null);
      setIsPlaying(false);
      setAnimationError(null);
      return;
    }

    // Reset selection state when switching characters
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

  // 2. Register finished listener for "Once" loop mode completion
  useEffect(() => {
    if (!characterId) return;

    const unsubscribe = animationRuntime.onFinished(characterId, () => {
      setIsPlaying(false);
    });

    return () => {
      unsubscribe();
    };
  }, [characterId, setIsPlaying]);

  if (!selectedCharacter) {
    return null;
  }

  // Handle Animation Selection
  const handleSelectAnimation = async (animId: string) => {
    if (!characterId) return;

    if (!animId) {
      animationRuntime.stop(characterId);
      setActiveAnimationId(null);
      setIsPlaying(false);
      setAnimationError(null);
      return;
    }

    const animData = animations.find((a) => a.id === animId);
    if (!animData) return;

    setIsAnimationLoading(true);
    setAnimationError(null);

    try {
      // Check if clip is already in runtime manager or needs loading via clip loader
      if (!animationRuntime.hasAnimationClip(characterId, animId)) {
        await animationClipLoader.loadAndBindClip(characterId, animData, animationRuntime);
      }
      setActiveAnimationId(animId);

      // Apply active speed and loop mode to newly loaded clip
      animationRuntime.setPlaybackSpeed(characterId, playbackSpeed);
      animationRuntime.setLoopMode(
        characterId,
        loopMode === "LOOP" ? THREE.LoopRepeat : THREE.LoopOnce
      );
    } catch (err: any) {
      console.error("Failed to load/bind animation clip:", err);
      setAnimationError(err.message || "Unable to load animation");
      setActiveAnimationId(null);
    } finally {
      setIsAnimationLoading(false);
    }
  };

  // Playback Control Handlers
  const handlePlay = () => {
    if (!characterId || !activeAnimationId) return;

    // Apply current speed & loop mode before playing
    animationRuntime.setPlaybackSpeed(characterId, playbackSpeed);
    animationRuntime.setLoopMode(
      characterId,
      loopMode === "LOOP" ? THREE.LoopRepeat : THREE.LoopOnce
    );

    const success = animationRuntime.play(characterId, activeAnimationId);
    if (success) {
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (!characterId) return;
    animationRuntime.pause(characterId);
    setIsPlaying(false);
  };

  const handleStop = () => {
    if (!characterId) return;
    animationRuntime.stop(characterId);
    setIsPlaying(false);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (characterId) {
      animationRuntime.setPlaybackSpeed(characterId, speed);
    }
  };

  const handleLoopModeToggle = (mode: "LOOP" | "ONCE") => {
    setLoopMode(mode);
    if (characterId) {
      animationRuntime.setLoopMode(
        characterId,
        mode === "LOOP" ? THREE.LoopRepeat : THREE.LoopOnce
      );
    }
  };

  const selectedAnimData = animations.find((a) => a.id === activeAnimationId);
  const speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

  return (
    <section className="space-y-3 border-t border-border pt-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-[0.2em] text-gold-soft flex items-center gap-1.5">
          <Film className="size-3.5 text-gold shrink-0" />
          Animation Playback
        </p>
        {isFetchingList && <Loader2 className="size-3 animate-spin text-gold" />}
      </div>

      {/* Animation Selector Dropdown */}
      <div className="space-y-1.5">
        <label className="text-[10px] text-muted-foreground block">Select Animation Clip</label>
        {isFetchingList ? (
          <div className="flex items-center gap-2 rounded border border-border bg-secondary/60 px-2.5 py-1.5 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin text-gold" />
            Loading character animations…
          </div>
        ) : animations.length === 0 ? (
          <div className="rounded border border-border bg-secondary/40 px-2.5 py-2 text-xs text-muted-foreground text-center">
            No animations available for this character.
          </div>
        ) : (
          <select
            value={activeAnimationId || ""}
            onChange={(e) => handleSelectAnimation(e.target.value)}
            disabled={isAnimationLoading}
            className="w-full rounded border border-border bg-secondary/80 px-2 py-1.5 text-xs text-foreground focus:border-gold focus:outline-none disabled:opacity-50"
            id="select-character-animation"
          >
            <option value="">-- Choose Animation --</option>
            {animations.map((anim) => (
              <option
                key={anim.id}
                value={anim.id}
                disabled={anim.status !== "READY"}
              >
                {anim.name} ({anim.animation_type}) — {anim.duration_seconds}s [{anim.status}]
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Loading Spinner Indicator */}
      {isAnimationLoading && (
        <div className="flex items-center gap-2 rounded-md border border-gold/30 bg-gold/5 px-2.5 py-1.5 text-xs text-gold animate-pulse">
          <Loader2 className="size-3.5 animate-spin shrink-0" />
          <span>Loading animation clip…</span>
        </div>
      )}

      {/* Error Alert Display */}
      {animationError && (
        <div className="flex items-center gap-2 rounded-md border border-red-500/40 bg-red-500/10 px-2.5 py-1.5 text-xs text-red-400">
          <AlertCircle className="size-3.5 shrink-0" />
          <span className="truncate">{animationError}</span>
        </div>
      )}

      {/* Metadata Overview Badge */}
      {selectedAnimData && (
        <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono">
          <div className="rounded bg-secondary/50 px-2 py-1 border border-border text-center">
            <span className="block text-[9px] text-muted-foreground">TYPE</span>
            <span className="text-gold font-semibold truncate block">{selectedAnimData.animation_type}</span>
          </div>
          <div className="rounded bg-secondary/50 px-2 py-1 border border-border text-center">
            <span className="block text-[9px] text-muted-foreground">DURATION</span>
            <span className="text-foreground font-semibold">{selectedAnimData.duration_seconds}s</span>
          </div>
          <div className="rounded bg-secondary/50 px-2 py-1 border border-border text-center">
            <span className="block text-[9px] text-muted-foreground">FPS</span>
            <span className="text-foreground font-semibold">{selectedAnimData.fps || 30}</span>
          </div>
        </div>
      )}

      {/* Playback Controls Toolbar: Play / Pause / Stop */}
      <div className="flex items-center gap-2">
        {!isPlaying ? (
          <button
            onClick={handlePlay}
            disabled={!activeAnimationId || isAnimationLoading}
            id="btn-anim-play"
            className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-gold px-3 py-1.5 text-xs font-semibold text-background hover:bg-gold/90 disabled:opacity-40 transition-colors shadow-sm"
          >
            <Play className="size-3.5 fill-current" />
            Play
          </button>
        ) : (
          <button
            onClick={handlePause}
            id="btn-anim-pause"
            className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-background hover:bg-amber-400 transition-colors shadow-sm"
          >
            <Pause className="size-3.5 fill-current" />
            Pause
          </button>
        )}

        <button
          onClick={handleStop}
          disabled={!activeAnimationId && !isPlaying}
          id="btn-anim-stop"
          className="flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary/80 px-3 py-1.5 text-xs font-medium text-foreground hover:border-gold/30 disabled:opacity-40 transition-colors"
          title="Stop & Reset Position"
        >
          <Square className="size-3.5 fill-current" />
          Stop
        </button>
      </div>

      {/* Playback Speed Selector */}
      <div className="space-y-1">
        <span className="text-[10px] text-muted-foreground block">Playback Speed</span>
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
          {speeds.map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`flex-1 rounded px-1.5 py-1 text-[10px] font-mono transition-colors border ${
                playbackSpeed === s
                  ? "border-gold/50 bg-gold/15 text-gold font-bold"
                  : "border-border bg-secondary/40 text-muted-foreground hover:text-foreground"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Loop Mode Selector */}
      <div className="space-y-1">
        <span className="text-[10px] text-muted-foreground block">Loop Mode</span>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={() => handleLoopModeToggle("LOOP")}
            className={`flex items-center justify-center gap-1 rounded py-1 text-xs transition-colors border ${
              loopMode === "LOOP"
                ? "border-gold/50 bg-gold/15 text-gold font-semibold"
                : "border-border bg-secondary/40 text-muted-foreground hover:text-foreground"
            }`}
          >
            <RefreshCw className="size-3" />
            Loop
          </button>
          <button
            onClick={() => handleLoopModeToggle("ONCE")}
            className={`flex items-center justify-center gap-1 rounded py-1 text-xs transition-colors border ${
              loopMode === "ONCE"
                ? "border-gold/50 bg-gold/15 text-gold font-semibold"
                : "border-border bg-secondary/40 text-muted-foreground hover:text-foreground"
            }`}
          >
            Once
          </button>
        </div>
      </div>
    </section>
  );
}
