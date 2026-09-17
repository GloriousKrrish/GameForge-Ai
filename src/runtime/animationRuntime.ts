import { AnimationRuntimeManager } from "./AnimationRuntimeManager";
import { AnimationClipLoader } from "./AnimationClipLoader";

/**
 * Global shared non-reactive runtime instances.
 * Keeps Three.js mixers, actions, and clip caches outside React/Zustand state loops.
 */
export const animationRuntime = new AnimationRuntimeManager();
export const animationClipLoader = new AnimationClipLoader();
