import * as THREE from "three";
import { AnimationRuntimeManager } from "./AnimationRuntimeManager";
import { AnimationClipLoader } from "./AnimationClipLoader";
import { useGameForgeStore } from "../store/useGameForgeStore";

/**
 * Phase 6D-C Unit & Integration Test Suite
 * 
 * Verifies animation playback controls, non-reactive runtime manager integration,
 * speed scaling, loop mode toggling, event synchronization, character switching,
 * loading/failure states, and Zustand state boundaries.
 */

function createMockRootObject(): THREE.Object3D {
  const root = new THREE.Object3D();
  root.name = "Armature";
  const hipBone = new THREE.Bone();
  hipBone.name = "Hips";
  root.add(hipBone);
  return root;
}

function createMockAnimationClip(name = "Walk", duration = 2.0): THREE.AnimationClip {
  const positionTrack = new THREE.VectorKeyframeTrack(
    "Hips.position",
    [0, 1, 2],
    [0, 0, 0, 0, 1, 0, 0, 0, 0]
  );
  return new THREE.AnimationClip(name, duration, [positionTrack]);
}

async function runPlaybackControlsTests() {
  console.log("=== RUNNING PHASE 6D-C ANIMATION PLAYBACK CONTROLS TESTS ===\n");

  let passed = 0;
  let total = 0;

  function assert(condition: boolean, message: string) {
    total++;
    if (condition) {
      passed++;
      console.log(`  ✓ ${message}`);
    } else {
      console.error(`  ✗ FAIL: ${message}`);
      throw new Error(`Assertion failed: ${message}`);
    }
  }

  // --- Test 1: Character selection & Zustand state reset ---
  console.log("--- Test 1: Character selection & state setup ---");
  {
    useGameForgeStore.getState().setSelectedCharacter({
      id: "char_alpha",
      name: "Alpha Hero",
      character_type: "HUMANOID",
      status: "READY",
      project_id: "proj_default",
      created_at: "",
      updated_at: "",
    });

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter?.id === "char_alpha", "Selected character is set to char_alpha");
    assert(store.activeAnimationId === null, "activeAnimationId initially null");
    assert(store.isPlaying === false, "isPlaying initially false");
    assert(store.playbackSpeed === 1.0, "playbackSpeed defaults to 1.0");
    assert(store.loopMode === "LOOP", "loopMode defaults to LOOP");
  }

  // --- Test 2: Non-character selected resets animation state ---
  console.log("\n--- Test 2: Non-character selected resets animation state ---");
  {
    useGameForgeStore.getState().setSelectedCharacter(null);
    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter === null, "selectedCharacter is null");
  }

  // --- Test 3: Play calls AnimationRuntimeManager correctly ---
  console.log("\n--- Test 3: Play calls AnimationRuntimeManager correctly ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Walk", 2.0);
    runtime.registerAnimationClip("char_1", "anim_walk", clip);

    assert(runtime.isPlaying("char_1") === false, "Not playing initially");
    const playSuccess = runtime.play("char_1", "anim_walk");
    assert(playSuccess === true, "play() returned true");
    assert(runtime.isPlaying("char_1") === true, "Character is playing after play()");
    runtime.dispose();
  }

  // --- Test 4: Pause preserves playback position ---
  console.log("\n--- Test 4: Pause preserves playback position ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Walk", 2.0);
    runtime.registerAnimationClip("char_1", "anim_walk", clip);

    runtime.play("char_1", "anim_walk");
    runtime.update(0.5); // Advance 0.5s
    const timeBeforePause = runtime.getCurrentTime("char_1");
    assert(timeBeforePause > 0, "Time advanced during play");

    const pauseSuccess = runtime.pause("char_1");
    assert(pauseSuccess === true, "pause() returned true");
    assert(runtime.isPlaying("char_1") === false, "Not playing after pause");
    const timeAfterPause = runtime.getCurrentTime("char_1");
    assert(timeAfterPause === timeBeforePause, "Pause preserves playback position");
    runtime.dispose();
  }

  // --- Test 5: Stop resets playback position to 0 ---
  console.log("\n--- Test 5: Stop resets playback position to 0 ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Walk", 2.0);
    runtime.registerAnimationClip("char_1", "anim_walk", clip);

    runtime.play("char_1", "anim_walk");
    runtime.update(0.5);
    assert(runtime.getCurrentTime("char_1") > 0, "Time advanced before stop");

    const stopSuccess = runtime.stop("char_1");
    assert(stopSuccess === true, "stop() returned true");
    assert(runtime.isPlaying("char_1") === false, "Not playing after stop");
    assert(runtime.getCurrentTime("char_1") === 0, "Stop resets position to 0");
    runtime.dispose();
  }

  // --- Test 6: Playback speed changes update mixer timescale ---
  console.log("\n--- Test 6: Playback speed changes update mixer timescale ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);

    const speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
    for (const speed of speeds) {
      const setOk = runtime.setPlaybackSpeed("char_1", speed);
      assert(setOk === true, `setPlaybackSpeed(${speed}) returned true`);
      const mixer = runtime.getMixer("char_1");
      assert(mixer?.timeScale === speed, `Mixer timeScale updated to ${speed}`);
    }
    runtime.dispose();
  }

  // --- Test 7: Loop mode toggling (Loop vs Once) ---
  console.log("\n--- Test 7: Loop mode toggling ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Walk", 2.0);
    runtime.registerAnimationClip("char_1", "anim_walk", clip);
    runtime.play("char_1", "anim_walk");

    const loopOk = runtime.setLoopMode("char_1", THREE.LoopRepeat);
    assert(loopOk === true, "setLoopMode(LoopRepeat) returned true");

    const onceOk = runtime.setLoopMode("char_1", THREE.LoopOnce);
    assert(onceOk === true, "setLoopMode(LoopOnce) returned true");
    runtime.dispose();
  }

  // --- Test 8: "Once" completion fires onFinished callback ---
  console.log("\n--- Test 8: Once completion fires onFinished callback ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    const mixer = runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Walk", 1.0);
    runtime.registerAnimationClip("char_1", "anim_walk", clip);

    let finishedFired = false;
    runtime.onFinished("char_1", () => {
      finishedFired = true;
    });

    runtime.play("char_1", "anim_walk");
    runtime.setLoopMode("char_1", THREE.LoopOnce);

    // Simulate mixer finished event dispatch
    mixer.dispatchEvent({ type: "finished", action: {} as any, direction: 1 });
    assert(finishedFired === true, "onFinished callback fired on finished event");
    runtime.dispose();
  }

  // --- Test 9: Character switching isolation ---
  console.log("\n--- Test 9: Character switching isolation ---");
  {
    const runtime = new AnimationRuntimeManager();
    const rootA = createMockRootObject();
    const rootB = createMockRootObject();

    runtime.registerCharacter("char_A", rootA);
    runtime.registerCharacter("char_B", rootB);

    const clipA = createMockAnimationClip("Walk_A", 2.0);
    const clipB = createMockAnimationClip("Walk_B", 3.0);

    runtime.registerAnimationClip("char_A", "anim_A", clipA);
    runtime.registerAnimationClip("char_B", "anim_B", clipB);

    runtime.play("char_A", "anim_A");
    assert(runtime.isPlaying("char_A") === true, "Char A playing");
    assert(runtime.isPlaying("char_B") === false, "Char B not playing");

    runtime.play("char_B", "anim_B");
    assert(runtime.isPlaying("char_A") === true, "Char A still playing independently");
    assert(runtime.isPlaying("char_B") === true, "Char B playing");

    runtime.unregisterCharacter("char_A");
    assert(runtime.hasCharacter("char_A") === false, "Char A unregistered");
    assert(runtime.hasCharacter("char_B") === true, "Char B survives Char A unregister");
    runtime.dispose();
  }

  // --- Test 10: Deleted character cleanup ---
  console.log("\n--- Test 10: Deleted character cleanup ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_doomed", root);
    const clip = createMockAnimationClip("Die", 1.0);
    runtime.registerAnimationClip("char_doomed", "anim_die", clip);

    runtime.play("char_doomed", "anim_die");
    runtime.unregisterCharacter("char_doomed");

    assert(runtime.hasCharacter("char_doomed") === false, "Character deleted from runtime");
    assert(runtime.getRegisteredAnimationIds("char_doomed").length === 0, "Clips cleared for deleted character");
    assert(runtime.isPlaying("char_doomed") === false, "Deleted character is not playing");
    runtime.dispose();
  }

  // --- Test 11: Loading and error state tracking ---
  console.log("\n--- Test 11: Loading and error state tracking ---");
  {
    const store = useGameForgeStore.getState();
    store.setIsAnimationLoading(true);
    assert(useGameForgeStore.getState().isAnimationLoading === true, "isAnimationLoading set to true");

    store.setIsAnimationLoading(false);
    assert(useGameForgeStore.getState().isAnimationLoading === false, "isAnimationLoading set to false");

    store.setAnimationError("Unable to load animation");
    assert(useGameForgeStore.getState().animationError === "Unable to load animation", "animationError set");

    store.setAnimationError(null);
    assert(useGameForgeStore.getState().animationError === null, "animationError cleared");
  }

  // --- Test 12: Clip loader binding with runtime ---
  console.log("\n--- Test 12: Clip loader binding with runtime ---");
  {
    const loader = new AnimationClipLoader();
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_test", root);

    const mockClip = createMockAnimationClip("Jump", 1.5);
    const action = loader.bindClipToCharacter("char_test", mockClip, runtime, "anim_jump");

    assert(action !== null, "Action created successfully");
    assert(runtime.hasAnimationClip("char_test", "anim_jump") === true, "Clip registered in runtime");
    assert(runtime.getRegisteredAnimationIds("char_test").includes("anim_jump"), "anim_jump listed in registered IDs");

    loader.dispose();
    runtime.dispose();
  }

  // --- Test 13: 60Hz Zustand safety verification ---
  console.log("\n--- Test 13: 60Hz Zustand safety verification ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    const storeInitialState = { ...useGameForgeStore.getState() };

    // Simulate 60 frames of update(0.016)
    for (let frame = 0; frame < 60; frame++) {
      runtime.update(0.016);
    }

    const storeAfter60Frames = { ...useGameForgeStore.getState() };
    assert(
      storeInitialState.isPlaying === storeAfter60Frames.isPlaying &&
      storeInitialState.activeAnimationId === storeAfter60Frames.activeAnimationId,
      "Zustand state was not mutated at 60Hz during render loop"
    );
    runtime.dispose();
  }

  // --- Test 14: Speed bounds safety ---
  console.log("\n--- Test 14: Speed bounds safety ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);

    runtime.setPlaybackSpeed("char_1", 0);
    const mixer = runtime.getMixer("char_1");
    assert(mixer?.timeScale === 0.01, "0 speed clamped to safe minimum 0.01");

    runtime.setPlaybackSpeed("char_1", -5);
    assert(mixer?.timeScale === 0.01, "Negative speed clamped to safe minimum 0.01");
    runtime.dispose();
  }

  // --- Test 15: Full playback controls lifecycle ---
  console.log("\n--- Test 15: Full playback controls lifecycle ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_full", root);

    const clipWalk = createMockAnimationClip("Walk", 2.0);
    const clipRun = createMockAnimationClip("Run", 1.0);

    runtime.registerAnimationClip("char_full", "anim_walk", clipWalk);
    runtime.registerAnimationClip("char_full", "anim_run", clipRun);

    // 1. Play Walk
    runtime.play("char_full", "anim_walk");
    assert(runtime.isPlaying("char_full") === true, "Walk playing");

    // 2. Pause Walk
    runtime.pause("char_full");
    assert(runtime.isPlaying("char_full") === false, "Walk paused");

    // 3. Switch to Run & Play
    runtime.play("char_full", "anim_run");
    assert(runtime.isPlaying("char_full") === true, "Run playing");

    // 4. Change Speed to 1.5x
    runtime.setPlaybackSpeed("char_full", 1.5);
    assert(runtime.getMixer("char_full")?.timeScale === 1.5, "Speed scaled to 1.5x");

    // 5. Stop
    runtime.stop("char_full");
    assert(runtime.isPlaying("char_full") === false, "Stopped cleanly");
    assert(runtime.getCurrentTime("char_full") === 0, "Time reset to 0");

    runtime.dispose();
  }

  console.log(`\n✅ ALL ${passed}/${total} PHASE 6D-C PLAYBACK CONTROLS TESTS PASSED!`);
}

runPlaybackControlsTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
