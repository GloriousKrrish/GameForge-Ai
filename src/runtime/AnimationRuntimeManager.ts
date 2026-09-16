import * as THREE from "three";

/**
 * AnimationRuntimeManager
 * 
 * Non-reactive, framework-independent Three.js animation runtime manager.
 * Manages AnimationMixer instances per character root, handling action creation,
 * clip caching, playback state, frame updates, and clean disposal.
 */
export class AnimationRuntimeManager {
  private characterMixers: Map<string, THREE.AnimationMixer> = new Map();
  private characterRoots: Map<string, THREE.Object3D> = new Map();
  private characterActions: Map<string, Map<string, THREE.AnimationAction>> = new Map();
  private characterClips: Map<string, Map<string, THREE.AnimationClip>> = new Map();
  private activeActions: Map<string, THREE.AnimationAction> = new Map();
  private activeAnimationIds: Map<string, string> = new Map();

  /**
   * Register a character Object3D root and create a dedicated THREE.AnimationMixer.
   */
  public registerCharacter(characterId: string, rootObject: THREE.Object3D): THREE.AnimationMixer {
    if (this.characterMixers.has(characterId)) {
      this.unregisterCharacter(characterId);
    }

    const mixer = new THREE.AnimationMixer(rootObject);
    this.characterMixers.set(characterId, mixer);
    this.characterRoots.set(characterId, rootObject);
    this.characterActions.set(characterId, new Map());
    this.characterClips.set(characterId, new Map());

    return mixer;
  }

  /**
   * Unregister a character and clean up all associated mixers, actions, and clip caches.
   */
  public unregisterCharacter(characterId: string): void {
    const mixer = this.characterMixers.get(characterId);
    const root = this.characterRoots.get(characterId);

    if (mixer) {
      mixer.stopAllAction();
      if (root) {
        mixer.uncacheRoot(root);
      }
      const clipsMap = this.characterClips.get(characterId);
      if (clipsMap) {
        for (const clip of clipsMap.values()) {
          mixer.uncacheClip(clip);
        }
      }
    }

    this.characterMixers.delete(characterId);
    this.characterRoots.delete(characterId);
    this.characterActions.delete(characterId);
    this.characterClips.delete(characterId);
    this.activeActions.delete(characterId);
    this.activeAnimationIds.delete(characterId);
  }

  public hasCharacter(characterId: string): boolean {
    return this.characterMixers.has(characterId);
  }

  public getMixer(characterId: string): THREE.AnimationMixer | undefined {
    return this.characterMixers.get(characterId);
  }

  /**
   * Register an AnimationClip with a character and return the created AnimationAction.
   */
  public registerAnimationClip(
    characterId: string,
    animationId: string,
    clip: THREE.AnimationClip
  ): THREE.AnimationAction {
    const mixer = this.characterMixers.get(characterId);
    if (!mixer) {
      throw new Error(`Character "${characterId}" is not registered in AnimationRuntimeManager.`);
    }

    const actionsMap = this.characterActions.get(characterId)!;
    const clipsMap = this.characterClips.get(characterId)!;

    clipsMap.set(animationId, clip);

    const action = mixer.clipAction(clip);
    actionsMap.set(animationId, action);

    return action;
  }

  /**
   * Load and register animation clips from GLTF animation array.
   */
  public loadAnimationFromGLTF(
    characterId: string,
    animationId: string,
    gltfAnimations: THREE.AnimationClip[],
    targetClipName?: string
  ): THREE.AnimationAction | null {
    if (!gltfAnimations || gltfAnimations.length === 0) {
      return null;
    }

    let clip: THREE.AnimationClip | undefined;

    if (targetClipName) {
      clip = gltfAnimations.find((c) => c.name === targetClipName);
    }

    if (!clip) {
      clip = gltfAnimations[0];
    }

    return this.registerAnimationClip(characterId, animationId, clip);
  }

  /**
   * Play an animation action for a character.
   */
  public play(characterId: string, animationId?: string): boolean {
    const actionsMap = this.characterActions.get(characterId);
    if (!actionsMap) return false;

    let targetAnimId = animationId || this.activeAnimationIds.get(characterId);

    if (!targetAnimId) {
      // Pick first available animation if none specified
      const firstKey = actionsMap.keys().next().value;
      if (!firstKey) return false;
      targetAnimId = firstKey;
    }

    const targetAction = actionsMap.get(targetAnimId);
    if (!targetAction) return false;

    const currentAction = this.activeActions.get(characterId);
    if (currentAction && currentAction !== targetAction) {
      currentAction.stop();
    }

    targetAction.paused = false;
    targetAction.play();

    this.activeActions.set(characterId, targetAction);
    this.activeAnimationIds.set(characterId, targetAnimId);

    return true;
  }

  /**
   * Pause animation for a character without resetting time.
   */
  public pause(characterId: string): boolean {
    const action = this.activeActions.get(characterId);
    if (!action) return false;

    action.paused = true;
    return true;
  }

  /**
   * Stop animation for a character and reset.
   */
  public stop(characterId: string): boolean {
    const action = this.activeActions.get(characterId);
    if (!action) return false;

    action.stop();
    action.reset();
    return true;
  }

  /**
   * Set playback time for the current active animation and evaluate pose immediately.
   */
  public setTime(characterId: string, targetTime: number): boolean {
    const action = this.activeActions.get(characterId);
    const mixer = this.characterMixers.get(characterId);
    if (!action || !mixer) return false;

    const duration = action.getClip().duration;
    const clampedTime = Math.max(0, Math.min(targetTime, duration));

    action.time = clampedTime;
    mixer.update(0); // Force immediate pose update in Three.js

    return true;
  }

  /**
   * Set playback speed (time scale) for a character mixer.
   */
  public setPlaybackSpeed(characterId: string, speed: number): boolean {
    const mixer = this.characterMixers.get(characterId);
    if (!mixer) return false;

    const safeSpeed = Math.max(0.01, speed);
    mixer.timeScale = safeSpeed;
    return true;
  }

  /**
   * Set loop mode for character's active animation.
   */
  public setLoopMode(characterId: string, loopMode: THREE.LoopMode): boolean {
    const action = this.activeActions.get(characterId);
    if (!action) return false;

    action.setLoop(loopMode, Infinity);
    return true;
  }

  /**
   * Get current playback time of the active action.
   */
  public getCurrentTime(characterId: string): number {
    const action = this.activeActions.get(characterId);
    return action ? action.time : 0;
  }

  /**
   * Get duration of the active animation.
   */
  public getDuration(characterId: string): number {
    const action = this.activeActions.get(characterId);
    return action ? action.getClip().duration : 0;
  }

  /**
   * Check if character is currently playing.
   */
  public isPlaying(characterId: string): boolean {
    const action = this.activeActions.get(characterId);
    return action ? action.isRunning() && !action.paused : false;
  }

  /**
   * Update all active character mixers.
   * Clamps frame delta to 0.1s max to avoid tab-switch timing spikes.
   */
  public update(delta: number): void {
    if (delta <= 0) return;
    const clampedDelta = Math.min(delta, 0.1);

    for (const mixer of this.characterMixers.values()) {
      mixer.update(clampedDelta);
    }
  }

  /**
   * Dispose all managed character mixers and clear all maps.
   */
  public dispose(): void {
    const characterIds = Array.from(this.characterMixers.keys());
    for (const id of characterIds) {
      this.unregisterCharacter(id);
    }
  }
}
