import React, { useRef, useEffect } from "react";
import { SkipBack, SkipForward, ChevronLeft, ChevronRight } from "lucide-react";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { animationRuntime } from "@/runtime/animationRuntime";

interface AnimationTimelineProps {
  characterId: string;
  activeAnimationId: string | null;
  duration: number;
  fps?: number;
  disabled?: boolean;
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return "00:00.00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  const mm = String(mins).padStart(2, "0");
  const ss = String(secs).padStart(2, "0");
  const xx = String(ms).padStart(2, "0");
  return `${mm}:${ss}.${xx}`;
}

export function AnimationTimeline({
  characterId,
  activeAnimationId,
  duration,
  fps = 30,
  disabled = false,
}: AnimationTimelineProps) {
  const isPlaying = useGameForgeStore((s) => s.isPlaying);
  const setIsPlaying = useGameForgeStore((s) => s.setIsPlaying);

  // DOM Refs for non-reactive 60Hz playhead updates
  const trackRef = useRef<HTMLDivElement | null>(null);
  const playheadRef = useRef<HTMLDivElement | null>(null);
  const progressFillRef = useRef<HTMLDivElement | null>(null);
  const timeLabelRef = useRef<HTMLSpanElement | null>(null);
  const frameLabelRef = useRef<HTMLSpanElement | null>(null);

  // Internal non-reactive interaction state
  const isDraggingRef = useRef(false);
  const wasPlayingBeforeDragRef = useRef(false);

  const safeDuration = isFinite(duration) && duration > 0 ? duration : 0;
  const safeFps = isFinite(fps) && fps > 0 ? fps : 30;
  const totalFrames = Math.max(1, Math.round(safeDuration * safeFps));

  // Helper to update DOM playhead elements non-reactively
  const updatePlayheadDOM = (targetTime: number) => {
    const clampedTime = Math.max(0, Math.min(targetTime, safeDuration));
    const ratio = safeDuration > 0 ? clampedTime / safeDuration : 0;
    const pct = (ratio * 100).toFixed(2);

    if (playheadRef.current) {
      playheadRef.current.style.left = `${pct}%`;
    }
    if (progressFillRef.current) {
      progressFillRef.current.style.width = `${pct}%`;
    }

    const currentFrame = Math.min(
      Math.round(clampedTime * safeFps) + 1,
      totalFrames
    );

    if (timeLabelRef.current) {
      timeLabelRef.current.textContent = `${formatTime(clampedTime)} / ${formatTime(safeDuration)}`;
    }
    if (frameLabelRef.current) {
      frameLabelRef.current.textContent = `Frame ${currentFrame} / ${totalFrames}`;
    }
  };

  // 1. Non-reactive RAF loop for playhead movement during playback
  useEffect(() => {
    if (!characterId || !activeAnimationId || disabled || safeDuration <= 0) {
      updatePlayheadDOM(0);
      return;
    }

    let rafId: number;

    const tick = () => {
      if (!isDraggingRef.current) {
        const curTime = animationRuntime.getCurrentTime(characterId);
        updatePlayheadDOM(curTime);
      }

      if (isPlaying) {
        rafId = requestAnimationFrame(tick);
      }
    };

    tick();

    return () => {
      cancelAnimationFrame(rafId);
    };
  }, [characterId, activeAnimationId, safeDuration, safeFps, isPlaying, disabled]);

  // 2. Helper to seek time from mouse/pointer X coordinate
  const seekFromPointerX = (clientX: number) => {
    if (!trackRef.current || !characterId || safeDuration <= 0) return;

    const rect = trackRef.current.getBoundingClientRect();
    if (rect.width <= 0) return;

    const rawRatio = (clientX - rect.left) / rect.width;
    const clampedRatio = Math.max(0, Math.min(1, rawRatio));
    const targetTime = clampedRatio * safeDuration;

    animationRuntime.setTime(characterId, targetTime);
    updatePlayheadDOM(targetTime);
  };

  // 3. Pointer Down handler (initiates scrubbing / dragging)
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!characterId || !activeAnimationId || safeDuration <= 0 || disabled) return;

    isDraggingRef.current = true;
    wasPlayingBeforeDragRef.current = isPlaying;

    if (isPlaying) {
      animationRuntime.pause(characterId);
      setIsPlaying(false);
    }

    seekFromPointerX(e.clientX);

    const handlePointerMove = (moveEv: PointerEvent) => {
      if (!isDraggingRef.current) return;
      seekFromPointerX(moveEv.clientX);
    };

    const handlePointerUp = () => {
      isDraggingRef.current = false;
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);

      if (wasPlayingBeforeDragRef.current && activeAnimationId) {
        animationRuntime.play(characterId, activeAnimationId);
        setIsPlaying(true);
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  };

  // 4. Quick Action Button Handlers
  const handleJumpToStart = () => {
    if (!characterId) return;
    animationRuntime.setTime(characterId, 0);
    updatePlayheadDOM(0);
  };

  const handleJumpToEnd = () => {
    if (!characterId || safeDuration <= 0) return;
    animationRuntime.setTime(characterId, safeDuration);
    updatePlayheadDOM(safeDuration);
  };

  const handleStepFrame = (deltaFrames: number) => {
    if (!characterId || safeDuration <= 0) return;
    const curTime = animationRuntime.getCurrentTime(characterId);
    const frameDuration = 1 / safeFps;
    const newTime = Math.max(0, Math.min(safeDuration, curTime + deltaFrames * frameDuration));
    animationRuntime.setTime(characterId, newTime);
    updatePlayheadDOM(newTime);
  };

  const isTimelineDisabled = disabled || !activeAnimationId || safeDuration <= 0;

  return (
    <div className="space-y-2 border-t border-border pt-2.5">
      {/* Time and Frame Labels Header */}
      <div className="flex items-center justify-between text-[10px] font-mono">
        <span ref={timeLabelRef} className="text-foreground font-semibold">
          00:00.00 / {formatTime(safeDuration)}
        </span>
        <span ref={frameLabelRef} className="text-gold-soft">
          Frame 1 / {totalFrames}
        </span>
      </div>

      {/* Scrubbing Track Container */}
      <div
        ref={trackRef}
        onPointerDown={handlePointerDown}
        className={`relative h-6 w-full flex items-center cursor-pointer select-none rounded-md bg-secondary/80 px-1 border border-border transition-colors ${
          isTimelineDisabled ? "opacity-50 pointer-events-none" : "hover:border-gold/40"
        }`}
        title={isTimelineDisabled ? "Timeline Unavailable" : "Click or drag to scrub animation time"}
        id="animation-timeline-track"
      >
        {/* Background Track Line */}
        <div className="relative h-1.5 w-full rounded-full bg-panel overflow-hidden">
          {/* Progress Fill Bar */}
          <div
            ref={progressFillRef}
            className="absolute left-0 top-0 h-full bg-gold transition-none"
            style={{ width: "0%" }}
          />
        </div>

        {/* Draggable Playhead Knob */}
        <div
          ref={playheadRef}
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 size-3.5 rounded-full border border-gold bg-gold shadow-md hover:scale-125 transition-transform"
          style={{ left: "0%" }}
        />
      </div>

      {/* Frame Stepping & Jump Controls Toolbar */}
      <div className="flex items-center justify-between gap-1 text-[10px]">
        <div className="flex items-center gap-1">
          <button
            onClick={handleJumpToStart}
            disabled={isTimelineDisabled}
            className="flex items-center justify-center rounded border border-border bg-secondary/60 p-1 text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            title="Jump to Start (0s)"
            id="btn-timeline-start"
          >
            <SkipBack className="size-3" />
          </button>
          <button
            onClick={() => handleStepFrame(-1)}
            disabled={isTimelineDisabled}
            className="flex items-center justify-center rounded border border-border bg-secondary/60 p-1 text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            title="Previous Frame"
            id="btn-timeline-prev-frame"
          >
            <ChevronLeft className="size-3" />
          </button>
        </div>

        <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-wider">
          {safeFps} FPS Scrub
        </span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => handleStepFrame(1)}
            disabled={isTimelineDisabled}
            className="flex items-center justify-center rounded border border-border bg-secondary/60 p-1 text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            title="Next Frame"
            id="btn-timeline-next-frame"
          >
            <ChevronRight className="size-3" />
          </button>
          <button
            onClick={handleJumpToEnd}
            disabled={isTimelineDisabled}
            className="flex items-center justify-center rounded border border-border bg-secondary/60 p-1 text-muted-foreground hover:text-foreground disabled:opacity-40 transition-colors"
            title="Jump to End"
            id="btn-timeline-end"
          >
            <SkipForward className="size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
