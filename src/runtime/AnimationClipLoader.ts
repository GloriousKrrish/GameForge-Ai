import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import type { AnimationRuntimeManager } from "./AnimationRuntimeManager";

// ── Types ────────────────────────────────────────────────────────────────────

/** Metadata about a discovered animation clip, kept lightweight for UI. */
export interface DiscoveredClip {
  clipName: string;
  duration: number;
  trackCount: number;
}

/** Result of loading and inspecting an animation GLB. */
export interface AnimationLoadResult {
  animationId: string;
  characterId: string;
  clips: DiscoveredClip[];
  selectedClipName: string;
  boundSuccessfully: boolean;
  error?: string;
}

/** Cached in-memory record for a loaded animation GLB. */
interface CachedAnimation {
  clips: THREE.AnimationClip[];
  discoveredClips: DiscoveredClip[];
}

// ── AnimationClipLoader ──────────────────────────────────────────────────────

/**
 * AnimationClipLoader
 *
 * Handles async GLB loading, clip discovery, validation, caching,
 * concurrent-load deduplication, and stale-request protection.
 *
 * Framework-independent. Does not depend on React or Zustand.
 * Owned by the viewport/runtime lifecycle.
 */
export class AnimationClipLoader {
  private loader: GLTFLoader;
  private cache: Map<string, CachedAnimation> = new Map();
  private inflightRequests: Map<string, Promise<CachedAnimation>> = new Map();
  private disposed = false;

  /**
   * Track the latest requested animation per character to prevent
   * stale async loads from overwriting newer selections.
   */
  private latestRequestGeneration: Map<string, number> = new Map();
  private requestCounter = 0;

  constructor(loader?: GLTFLoader) {
    this.loader = loader || new GLTFLoader();
  }

  // ── GLB Loading & Clip Discovery ─────────────────────────────────────────

  /**
   * Load an animation GLB from a URL, discover clips, validate, and cache.
   * Deduplicates concurrent requests for the same animationId.
   */
  public async loadAnimationGLB(
    animationId: string,
    glbUrl: string
  ): Promise<CachedAnimation> {
    if (this.disposed) {
      throw new Error("AnimationClipLoader has been disposed.");
    }

    // Return from cache if already loaded
    const cached = this.cache.get(animationId);
    if (cached) return cached;

    // Deduplicate in-flight requests
    const inflight = this.inflightRequests.get(animationId);
    if (inflight) return inflight;

    // Start new load
    const loadPromise = this._doLoad(animationId, glbUrl);
    this.inflightRequests.set(animationId, loadPromise);

    try {
      const result = await loadPromise;
      return result;
    } finally {
      this.inflightRequests.delete(animationId);
    }
  }

  private async _doLoad(
    animationId: string,
    glbUrl: string
  ): Promise<CachedAnimation> {
    // Resolve URL: prefix with backend base if relative
    const resolvedUrl = glbUrl.startsWith("http")
      ? glbUrl
      : `http://localhost:8000${glbUrl}`;

    let gltf;
    try {
      gltf = await this.loader.loadAsync(resolvedUrl);
    } catch (err) {
      throw new Error(
        `Failed to load animation GLB for "${animationId}" from ${resolvedUrl}: ${err instanceof Error ? err.message : String(err)}`
      );
    }

    const animations = gltf.animations;
    if (!animations || animations.length === 0) {
      throw new Error(
        `Animation GLB for "${animationId}" contains zero animation clips.`
      );
    }

    // Validate each clip
    const discoveredClips: DiscoveredClip[] = [];
    for (const clip of animations) {
      if (!clip || !isFinite(clip.duration) || clip.duration <= 0) {
        console.warn(
          `[AnimationClipLoader] Skipping invalid clip "${clip?.name}" in animation "${animationId}" (duration=${clip?.duration})`
        );
        continue;
      }
      if (!clip.tracks || clip.tracks.length === 0) {
        console.warn(
          `[AnimationClipLoader] Skipping clip "${clip.name}" with zero tracks in animation "${animationId}"`
        );
        continue;
      }
      discoveredClips.push({
        clipName: clip.name,
        duration: clip.duration,
        trackCount: clip.tracks.length,
      });
    }

    if (discoveredClips.length === 0) {
      throw new Error(
        `Animation GLB for "${animationId}" has no valid clips (all clips had zero duration or zero tracks).`
      );
    }

    const result: CachedAnimation = {
      clips: animations.filter(
        (c) => c && isFinite(c.duration) && c.duration > 0 && c.tracks?.length > 0
      ),
      discoveredClips,
    };

    this.cache.set(animationId, result);
    return result;
  }

  // ── Clip Selection ───────────────────────────────────────────────────────

  /**
   * Select a clip from a loaded animation's clip array.
   *
   * Priority:
   * 1. Exact name match (targetClipName)
   * 2. Case-insensitive/normalized match
   * 3. If exactly 1 clip, use it
   * 4. Fail with available clip names
   */
  public selectClip(
    clips: THREE.AnimationClip[],
    animationId: string,
    targetClipName?: string
  ): THREE.AnimationClip {
    if (!clips || clips.length === 0) {
      throw new Error(`No clips available for animation "${animationId}".`);
    }

    // 1. Exact name match
    if (targetClipName) {
      const exact = clips.find((c) => c.name === targetClipName);
      if (exact) return exact;

      // 2. Normalized match (case-insensitive)
      const normalized = targetClipName.toLowerCase().trim();
      const fuzzy = clips.find(
        (c) => c.name.toLowerCase().trim() === normalized
      );
      if (fuzzy) return fuzzy;
    }

    // 3. Single clip — use it
    if (clips.length === 1) {
      return clips[0];
    }

    // 4. Multiple clips but no specific name requested — deterministic first
    if (!targetClipName) {
      return clips[0];
    }

    // 5. Fail: specific name requested but not found among multiple
    const available = clips.map((c) => `"${c.name}"`).join(", ");
    throw new Error(
      `Clip "${targetClipName}" not found in animation "${animationId}". Available: ${available}`
    );
  }

  // ── Character Binding ────────────────────────────────────────────────────

  /**
   * Load an animation GLB, discover clips, select the target clip,
   * validate character ownership, and bind to the AnimationRuntimeManager.
   *
   * Includes stale-request protection: if a newer loadAndBind call arrives
   * for the same character before this one resolves, this result is discarded.
   */
  public async loadAndBind(
    runtimeManager: AnimationRuntimeManager,
    characterId: string,
    animationId: string,
    glbUrl: string,
    expectedCharacterIdFromModel: string,
    targetClipName?: string
  ): Promise<AnimationLoadResult> {
    // Enforce character ownership
    if (characterId !== expectedCharacterIdFromModel) {
      return {
        animationId,
        characterId,
        clips: [],
        selectedClipName: "",
        boundSuccessfully: false,
        error: `Character ownership mismatch: binding character "${characterId}" but animation belongs to "${expectedCharacterIdFromModel}".`,
      };
    }

    // Verify character is registered in runtime
    if (!runtimeManager.hasCharacter(characterId)) {
      return {
        animationId,
        characterId,
        clips: [],
        selectedClipName: "",
        boundSuccessfully: false,
        error: `Character "${characterId}" is not registered in AnimationRuntimeManager.`,
      };
    }

    // Stale-request generation tracking
    const generation = ++this.requestCounter;
    this.latestRequestGeneration.set(characterId, generation);

    try {
      const cached = await this.loadAnimationGLB(animationId, glbUrl);

      // Stale check: if a newer request was issued while we were loading, abort
      if (this.latestRequestGeneration.get(characterId) !== generation) {
        return {
          animationId,
          characterId,
          clips: cached.discoveredClips,
          selectedClipName: "",
          boundSuccessfully: false,
          error: "Stale request: a newer animation was requested for this character.",
        };
      }

      const selectedClip = this.selectClip(
        cached.clips,
        animationId,
        targetClipName
      );

      // Validate clip tracks can resolve (basic check)
      if (
        !selectedClip.tracks ||
        selectedClip.tracks.length === 0 ||
        !isFinite(selectedClip.duration) ||
        selectedClip.duration <= 0
      ) {
        return {
          animationId,
          characterId,
          clips: cached.discoveredClips,
          selectedClipName: selectedClip.name,
          boundSuccessfully: false,
          error: `Selected clip "${selectedClip.name}" has invalid tracks or duration.`,
        };
      }

      // Bind to runtime manager
      runtimeManager.registerAnimationClip(
        characterId,
        animationId,
        selectedClip
      );

      return {
        animationId,
        characterId,
        clips: cached.discoveredClips,
        selectedClipName: selectedClip.name,
        boundSuccessfully: true,
      };
    } catch (err) {
      return {
        animationId,
        characterId,
        clips: [],
        selectedClipName: "",
        boundSuccessfully: false,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  /**
   * Convenience wrapper to load and bind an animation clip given an AnimationData record.
   */
  public async loadAndBindClip(
    characterId: string,
    animData: { id: string; character_id: string; glb_url?: string | null; name?: string },
    runtimeManager: AnimationRuntimeManager
  ): Promise<AnimationLoadResult> {
    const glbUrl = animData.glb_url || `/exports/${animData.id}.glb`;
    return this.loadAndBind(
      runtimeManager,
      characterId,
      animData.id,
      glbUrl,
      animData.character_id,
      animData.name
    );
  }

  /**
   * Direct clip binding helper for runtime instances and test mocks.
   */
  public bindClipToCharacter(
    characterId: string,
    clip: THREE.AnimationClip,
    runtimeManager: AnimationRuntimeManager,
    animationId = "custom_clip"
  ): THREE.AnimationAction {
    return runtimeManager.registerAnimationClip(characterId, animationId, clip);
  }

  // ── Query ────────────────────────────────────────────────────────────────

  /** Get discovered clips for an already-loaded animation. */
  public getDiscoveredClips(animationId: string): DiscoveredClip[] | undefined {
    return this.cache.get(animationId)?.discoveredClips;
  }

  /** Check if an animation GLB is already cached. */
  public isCached(animationId: string): boolean {
    return this.cache.has(animationId);
  }

  /** Check if an animation is currently loading. */
  public isLoading(animationId: string): boolean {
    return this.inflightRequests.has(animationId);
  }

  // ── Cleanup ──────────────────────────────────────────────────────────────

  /** Remove a single animation from the cache. */
  public uncache(animationId: string): void {
    this.cache.delete(animationId);
  }

  /** Dispose all cached data and mark as disposed. */
  public dispose(): void {
    this.disposed = true;
    this.cache.clear();
    this.inflightRequests.clear();
    this.latestRequestGeneration.clear();
  }
}
