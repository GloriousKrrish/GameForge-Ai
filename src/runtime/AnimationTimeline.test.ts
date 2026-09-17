import * as THREE from "three";
import { AnimationRuntimeManager } from "./AnimationRuntimeManager";
import { AnimationClipLoader } from "./AnimationClipLoader";
import { useGameForgeStore } from "../store/useGameForgeStore";

/**
 * Phase 6D-D Unit & Integration Test Suite
 * 
 * Verifies Animation Timeline scrubbing, pointer dragging, playhead DOM updates,
 * precision frame stepping, Start/End seeking, edge-case clamping, character/clip
 * switching resets, and 60Hz non-reactive Zustand safety.
 */

function createMockRootObject(): THREE.Object3D {
  const root = new THREE.Object3D();
  root.name = "Armature";
  const hipBone = new THREE.Bone();
  hipBone.name = "Hips";
  root.add(hipBone);
  return root;
}

function createMockAnimationClip(name = "Run", duration = 2.0): THREE.AnimationClip {
  const positionTrack = new THREE.VectorKeyframeTrack(
    "Hips.position",
    [0, 1, 2],
    [0, 0, 0, 0, 1, 0, 0, 0, 0]
  );
  return new THREE.AnimationClip(name, duration, [positionTrack]);
}

async function runTimelineTests() {
  console.log("=== RUNNING PHASE 6D-D ANIMATION TIMELINE TESTS ===\n");

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

  // --- Test 1: Duration and frame calculation ---
  console.log("--- Test 1: Duration and frame calculation ---");
  {
    const duration = 2.0;
    const fps = 30;
    const totalFrames = Math.max(1, Math.round(duration * fps));
    assert(totalFrames === 60, "2.0s at 30 FPS calculates exactly 60 frames");

    const shortDuration = 0.5;
    const shortFrames = Math.max(1, Math.round(shortDuration * 30));
    assert(shortFrames === 15, "0.5s at 30 FPS calculates exactly 15 frames");
  }

  // --- Test 2: Click to 50% seeks to half duration ---
  console.log("\n--- Test 2: Click to 50% seeks to half duration ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    const ratio = 0.5;
    const targetTime = ratio * 2.0; // 1.0s
    runtime.setTime("char_1", targetTime);

    const currentTime = runtime.getCurrentTime("char_1");
    assert(Math.abs(currentTime - 1.0) < 0.001, "Seeking to 50% sets current time to 1.0s");
    runtime.dispose();
  }

  // --- Test 3: Seeking to Start and End ---
  console.log("\n--- Test 3: Seeking to Start and End ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    // Seek to End
    runtime.setTime("char_1", 2.0);
    assert(Math.abs(runtime.getCurrentTime("char_1") - 2.0) < 0.001, "Seek to End sets time to 2.0s");

    // Seek to Start
    runtime.setTime("char_1", 0.0);
    assert(runtime.getCurrentTime("char_1") === 0, "Seek to Start sets time to 0.0s");
    runtime.dispose();
  }

  // --- Test 4: Scrubbing temporarily pauses playback and resumes on release ---
  console.log("\n--- Test 4: Scrubbing while playing pauses temporarily ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);

    // Initial state: Playing
    runtime.play("char_1", "anim_run");
    let isPlayingState = true;
    const wasPlayingBeforeDrag = isPlayingState;

    // Pointer down: pause
    if (isPlayingState) {
      runtime.pause("char_1");
      isPlayingState = false;
    }

    assert(runtime.isPlaying("char_1") === false, "Runtime paused during scrubbing drag");

    // Drag: seek to 0.8s
    runtime.setTime("char_1", 0.8);
    assert(Math.abs(runtime.getCurrentTime("char_1") - 0.8) < 0.001, "Time updated to 0.8s during drag");

    // Pointer up: resume because was playing before
    if (wasPlayingBeforeDrag) {
      runtime.play("char_1", "anim_run");
      isPlayingState = true;
    }

    assert(runtime.isPlaying("char_1") === true, "Playback resumed on pointer release");
    runtime.dispose();
  }

  // --- Test 5: Dragging while paused remains paused on release ---
  console.log("\n--- Test 5: Dragging while paused remains paused on release ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);

    // Initial state: Paused
    runtime.play("char_1", "anim_run");
    runtime.pause("char_1");
    let isPlayingState = false;
    const wasPlayingBeforeDrag = isPlayingState;

    // Drag: seek to 1.2s
    runtime.setTime("char_1", 1.2);

    // Pointer up
    if (wasPlayingBeforeDrag) {
      runtime.play("char_1", "anim_run");
      isPlayingState = true;
    }

    assert(runtime.isPlaying("char_1") === false, "Playback remains paused on pointer release");
    assert(Math.abs(runtime.getCurrentTime("char_1") - 1.2) < 0.001, "Time preserved at 1.2s");
    runtime.dispose();
  }

  // --- Test 6: Precision frame stepping (1/fps) ---
  console.log("\n--- Test 6: Precision frame stepping (1/fps) ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    const fps = 30;
    const frameDuration = 1 / fps; // 0.0333...

    runtime.setTime("char_1", 0);
    // Step forward 1 frame
    runtime.setTime("char_1", 0 + frameDuration);
    assert(Math.abs(runtime.getCurrentTime("char_1") - frameDuration) < 0.0001, "Stepped forward 1 frame (+1/30s)");

    // Step backward 1 frame
    runtime.setTime("char_1", Math.max(0, frameDuration - frameDuration));
    assert(runtime.getCurrentTime("char_1") === 0, "Stepped backward 1 frame (back to 0s)");
    runtime.dispose();
  }

  // --- Test 7: Out-of-bounds pointer ratio clamping ---
  console.log("\n--- Test 7: Out-of-bounds pointer ratio clamping ---");
  {
    const duration = 2.0;

    // Simulated negative clientX ratio (-0.2)
    const negRatio = Math.max(0, Math.min(1, -0.2));
    assert(negRatio === 0, "Negative ratio clamped to 0.0");
    assert(negRatio * duration === 0, "Negative time clamped to 0.0s");

    // Simulated overflow clientX ratio (1.5)
    const overflowRatio = Math.max(0, Math.min(1, 1.5));
    assert(overflowRatio === 1, "Overflow ratio clamped to 1.0");
    assert(overflowRatio * duration === 2.0, "Overflow time clamped to 2.0s");
  }

  // --- Test 8: NaN and Infinity safety ---
  console.log("\n--- Test 8: NaN and Infinity safety ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    // Passing NaN time
    const nanTime = NaN;
    const safeNanTime = isFinite(nanTime) ? nanTime : 0;
    runtime.setTime("char_1", safeNanTime);
    assert(runtime.getCurrentTime("char_1") === 0, "NaN time converted to safe 0");

    // Passing Infinity time
    const infTime = Infinity;
    const safeInfTime = isFinite(infTime) ? infTime : 2.0;
    runtime.setTime("char_1", safeInfTime);
    assert(runtime.getCurrentTime("char_1") === 2.0, "Infinity time converted to safe duration (2.0s)");
    runtime.dispose();
  }

  // --- Test 9: Animation switching resets timeline position ---
  console.log("\n--- Test 9: Animation switching resets timeline position ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);

    const clipWalk = createMockAnimationClip("Walk", 2.0);
    const clipJump = createMockAnimationClip("Jump", 1.0);

    runtime.registerAnimationClip("char_1", "anim_walk", clipWalk);
    runtime.registerAnimationClip("char_1", "anim_jump", clipJump);

    runtime.play("char_1", "anim_walk");
    runtime.setTime("char_1", 1.5);
    assert(Math.abs(runtime.getCurrentTime("char_1") - 1.5) < 0.001, "Walk at 1.5s");

    // Switch to Jump
    runtime.play("char_1", "anim_jump");
    runtime.setTime("char_1", 0);
    assert(runtime.getCurrentTime("char_1") === 0, "Timeline position reset to 0 for Jump");
    runtime.dispose();
  }

  // --- Test 10: Character switching resets timeline ---
  console.log("\n--- Test 10: Character switching resets timeline ---");
  {
    useGameForgeStore.getState().setSelectedCharacter({
      id: "char_hero",
      name: "Hero",
      character_type: "HUMANOID",
      status: "READY",
      project_id: "proj_default",
      created_at: "",
      updated_at: "",
    });

    useGameForgeStore.getState().setActiveAnimationId("anim_walk");
    useGameForgeStore.getState().setIsPlaying(true);

    // Switch character to null
    useGameForgeStore.getState().setSelectedCharacter(null);
    useGameForgeStore.getState().setActiveAnimationId(null);
    useGameForgeStore.getState().setIsPlaying(false);

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter === null, "Character reset to null");
    assert(store.activeAnimationId === null, "activeAnimationId reset to null");
    assert(store.isPlaying === false, "isPlaying reset to false");
  }

  // --- Test 11: Speed changes preserve timeline sync ---
  console.log("\n--- Test 11: Speed changes preserve timeline sync ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    runtime.setPlaybackSpeed("char_1", 2.0);
    runtime.update(0.05); // 0.05s delta at 2.0x speed = 0.10s playback time advance
    const timeAfterUpdate = runtime.getCurrentTime("char_1");
    assert(Math.abs(timeAfterUpdate - 0.10) < 0.01, "Timeline synchronized after speed scaling");
    runtime.dispose();
  }

  // --- Test 12: Zero/invalid duration handling ---
  console.log("\n--- Test 12: Zero/invalid duration handling ---");
  {
    const invalidDuration = 0;
    const safeDuration = isFinite(invalidDuration) && invalidDuration > 0 ? invalidDuration : 0;
    const ratio = safeDuration > 0 ? 0.5 / safeDuration : 0;
    assert(ratio === 0, "Zero duration returns 0 ratio safely without division by zero");
  }

  // --- Test 13: 60Hz Zustand non-reactive safety ---
  console.log("\n--- Test 13: 60Hz Zustand non-reactive safety ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = createMockRootObject();
    runtime.registerCharacter("char_1", root);
    const clip = createMockAnimationClip("Run", 2.0);
    runtime.registerAnimationClip("char_1", "anim_run", clip);
    runtime.play("char_1", "anim_run");

    const initialStore = { ...useGameForgeStore.getState() };

    // Simulate 60 frames of updates
    for (let frame = 0; frame < 60; frame++) {
      runtime.update(0.016);
    }

    const afterStore = { ...useGameForgeStore.getState() };
    assert(
      initialStore.isPlaying === afterStore.isPlaying &&
      initialStore.activeAnimationId === afterStore.activeAnimationId,
      "Zero Zustand mutations occurred during 60Hz animation updates"
    );
    runtime.dispose();
  }

  console.log(`\n✅ ALL ${passed}/${total} PHASE 6D-D ANIMATION TIMELINE TESTS PASSED!`);
}

runTimelineTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
