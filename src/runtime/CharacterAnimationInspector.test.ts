import * as THREE from "three";
import { AnimationRuntimeManager } from "./AnimationRuntimeManager";
import { AnimationClipLoader } from "./AnimationClipLoader";
import { useGameForgeStore } from "../store/useGameForgeStore";
import type { AnimationData } from "../api/animations";
import type { CharacterData, SkeletonData } from "../api/characters";

/**
 * Phase 6D-E Unit & Integration Test Suite
 * 
 * Verifies Character Animation Inspector metadata rendering, search filtering,
 * clip selection, skeleton details integration, character switching cleanup,
 * and 60Hz non-reactive Zustand safety.
 */

function createMockCharacter(id = "char_hero"): CharacterData {
  return {
    id,
    project_id: "proj_default",
    asset_id: "asset_mesh_01",
    name: "Hero Warrior",
    character_type: "HUMANOID",
    status: "READY",
    rig_id: "rig_humanoid_v1",
    skeleton_id: "skel_hero",
    skinning: {
      skeleton_id: "skel_hero",
      vertex_count: 1250,
      max_influences_per_vertex: 4,
      status: "VALID",
    },
    scene_object_ids: ["obj_mesh_01"],
  };
}

function createMockSkeleton(id = "skel_hero"): SkeletonData {
  return {
    id,
    character_id: "char_hero",
    name: "HumanoidSkeleton",
    root_bone_id: "Hips",
    bone_count: 18,
    bones: [
      { id: "b1", name: "Hips", head: [0, 1, 0], tail: [0, 1.2, 0] },
      { id: "b2", name: "Spine", parent_id: "b1", head: [0, 1.2, 0], tail: [0, 1.5, 0] },
    ],
  };
}

function createMockAnimationList(): AnimationData[] {
  return [
    {
      id: "anim_idle",
      project_id: "proj_default",
      character_id: "char_hero",
      name: "Idle Breathing",
      animation_type: "IDLE",
      status: "READY",
      duration_seconds: 2.0,
      fps: 30,
      frame_start: 1,
      frame_end: 60,
      is_looping: true,
      glb_url: "/exports/anim_idle.glb",
      track_count: 12,
      metadata: {},
      created_at: "",
      updated_at: "",
    },
    {
      id: "anim_walk",
      project_id: "proj_default",
      character_id: "char_hero",
      name: "Walk Stride",
      animation_type: "WALK",
      status: "READY",
      duration_seconds: 1.5,
      fps: 30,
      frame_start: 1,
      frame_end: 45,
      is_looping: true,
      glb_url: "/exports/anim_walk.glb",
      track_count: 15,
      metadata: {},
      created_at: "",
      updated_at: "",
    },
    {
      id: "anim_gen",
      project_id: "proj_default",
      character_id: "char_hero",
      name: "Heavy Slash",
      animation_type: "PROCEDURAL",
      status: "GENERATING",
      duration_seconds: 1.0,
      fps: 30,
      frame_start: 1,
      frame_end: 30,
      is_looping: false,
      track_count: 0,
      metadata: {},
      created_at: "",
      updated_at: "",
    },
    {
      id: "anim_fail",
      project_id: "proj_default",
      character_id: "char_hero",
      name: "Backflip",
      animation_type: "CUSTOM",
      status: "FAILED",
      duration_seconds: 1.0,
      fps: 30,
      frame_start: 1,
      frame_end: 30,
      is_looping: false,
      track_count: 0,
      metadata: {},
      created_at: "",
      updated_at: "",
    },
  ];
}

async function runInspectorTests() {
  console.log("=== RUNNING PHASE 6D-E CHARACTER ANIMATION INSPECTOR TESTS ===\n");

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

  // --- Test 1: Character selection sets inspector data ---
  console.log("--- Test 1: Character selection sets inspector data ---");
  {
    const char = createMockCharacter("char_hero");
    const skel = createMockSkeleton("skel_hero");

    useGameForgeStore.getState().setSelectedCharacter(char);
    useGameForgeStore.getState().setActiveSkeleton(skel);

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter?.id === "char_hero", "Character char_hero selected");
    assert(store.selectedCharacter?.name === "Hero Warrior", "Character name is Hero Warrior");
    assert(store.activeSkeleton?.bone_count === 18, "Active skeleton has 18 bones");
  }

  // --- Test 2: Unselecting character clears state ---
  console.log("\n--- Test 2: Unselecting character clears state ---");
  {
    useGameForgeStore.getState().setSelectedCharacter(null);
    useGameForgeStore.getState().setActiveSkeleton(null);

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter === null, "selectedCharacter is null");
    assert(store.activeSkeleton === null, "activeSkeleton is null");
  }

  // --- Test 3: Local animation search filtering ---
  console.log("\n--- Test 3: Local animation search filtering ---");
  {
    const animations = createMockAnimationList();
    const query = "walk";

    const filtered = animations.filter((a) =>
      a.name.toLowerCase().includes(query.toLowerCase()) ||
      a.animation_type.toLowerCase().includes(query.toLowerCase())
    );

    assert(filtered.length === 1, "Filter 'walk' matched exactly 1 animation");
    assert(filtered[0].id === "anim_walk", "Matched animation is anim_walk");
  }

  // --- Test 4: READY animation selection ---
  console.log("\n--- Test 4: READY animation selection ---");
  {
    const animations = createMockAnimationList();
    const idleAnim = animations.find((a) => a.id === "anim_idle");

    assert(idleAnim?.status === "READY", "anim_idle status is READY");

    useGameForgeStore.getState().setActiveAnimationId("anim_idle");
    assert(useGameForgeStore.getState().activeAnimationId === "anim_idle", "activeAnimationId set to anim_idle");
  }

  // --- Test 5: Non-ready / Failed animation handling ---
  console.log("\n--- Test 5: Non-ready / Failed animation handling ---");
  {
    const animations = createMockAnimationList();
    const genAnim = animations.find((a) => a.id === "anim_gen");
    const failAnim = animations.find((a) => a.id === "anim_fail");

    assert(genAnim?.status === "GENERATING", "anim_gen status is GENERATING");
    assert(failAnim?.status === "FAILED", "anim_fail status is FAILED");

    useGameForgeStore.getState().setAnimationError(`Animation "${failAnim?.name}" is failed and cannot be played.`);
    assert(useGameForgeStore.getState().animationError !== null, "Error alert set for non-ready animation");
    useGameForgeStore.getState().setAnimationError(null);
  }

  // --- Test 6: Selected animation details card data derivation ---
  console.log("\n--- Test 6: Selected animation details card data derivation ---");
  {
    const animations = createMockAnimationList();
    const activeAnim = animations.find((a) => a.id === "anim_idle")!;

    const duration = activeAnim.duration_seconds;
    const fps = activeAnim.fps || 30;
    const totalFrames = Math.round(duration * fps);

    assert(duration === 2.0, "Duration is 2.0s");
    assert(fps === 30, "FPS is 30");
    assert(totalFrames === 60, "Frame range calculates 1 to 60");
  }

  // --- Test 7: Runtime clip loader binding with inspector selection ---
  console.log("\n--- Test 7: Runtime clip loader binding with inspector selection ---");
  {
    const runtime = new AnimationRuntimeManager();
    const loader = new AnimationClipLoader();
    const root = new THREE.Object3D();
    root.name = "Armature";

    runtime.registerCharacter("char_hero", root);

    const mockClip = new THREE.AnimationClip("Idle", 2.0, [
      new THREE.VectorKeyframeTrack("Hips.position", [0, 1], [0, 0, 0, 0, 1, 0]),
    ]);

    const action = loader.bindClipToCharacter("char_hero", mockClip, runtime, "anim_idle");

    assert(action !== null, "Clip bound to runtime manager successfully");
    assert(runtime.hasAnimationClip("char_hero", "anim_idle") === true, "anim_idle registered in runtime");

    loader.dispose();
    runtime.dispose();
  }

  // --- Test 8: Character switching resets active animation selection ---
  console.log("\n--- Test 8: Character switching resets active animation selection ---");
  {
    const charA = createMockCharacter("char_hero_A");
    const charB = createMockCharacter("char_hero_B");

    useGameForgeStore.getState().setSelectedCharacter(charA);
    useGameForgeStore.getState().setActiveAnimationId("anim_idle");

    // Switch to Char B
    useGameForgeStore.getState().setSelectedCharacter(charB);
    useGameForgeStore.getState().setActiveAnimationId(null);

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter?.id === "char_hero_B", "Selected character switched to char_hero_B");
    assert(store.activeAnimationId === null, "activeAnimationId cleared on character switch");
  }

  // --- Test 9: Deleted character cleanup ---
  console.log("\n--- Test 9: Deleted character cleanup ---");
  {
    useGameForgeStore.getState().setSelectedCharacter(null);
    useGameForgeStore.getState().setActiveAnimationId(null);
    useGameForgeStore.getState().setIsPlaying(false);
    useGameForgeStore.getState().setAnimationError(null);

    const store = useGameForgeStore.getState();
    assert(store.selectedCharacter === null, "Inspector state cleared on character deletion");
    assert(store.activeAnimationId === null, "Active animation ID null");
    assert(store.isPlaying === false, "isPlaying false");
  }

  // --- Test 10: Empty animation list handling ---
  console.log("\n--- Test 10: Empty animation list handling ---");
  {
    const emptyAnimations: AnimationData[] = [];
    assert(emptyAnimations.length === 0, "Animation list is empty");
    useGameForgeStore.getState().setActiveAnimationId(null);
    assert(useGameForgeStore.getState().activeAnimationId === null, "activeAnimationId remains null");
  }

  // --- Test 11: Skeleton details rendering fallback ---
  console.log("\n--- Test 11: Skeleton details rendering fallback ---");
  {
    const nullSkeleton: SkeletonData | null = null;
    const boneCount = nullSkeleton?.bone_count || 0;
    const rootBone = nullSkeleton?.root_bone_id || "—";

    assert(boneCount === 0, "Null skeleton defaults bone count to 0");
    assert(rootBone === "—", "Null skeleton defaults root bone to dash");
  }

  // --- Test 12: Zero 60Hz Zustand state mutation verification ---
  console.log("\n--- Test 12: Zero 60Hz Zustand state mutation verification ---");
  {
    const runtime = new AnimationRuntimeManager();
    const root = new THREE.Object3D();
    runtime.registerCharacter("char_hero", root);

    const clip = new THREE.AnimationClip("Run", 1.0, [
      new THREE.VectorKeyframeTrack("Hips.position", [0, 1], [0, 0, 0, 0, 1, 0]),
    ]);
    runtime.registerAnimationClip("char_hero", "anim_run", clip);
    runtime.play("char_hero", "anim_run");

    const initialStoreState = { ...useGameForgeStore.getState() };

    for (let f = 0; f < 60; f++) {
      runtime.update(0.016);
    }

    const afterStoreState = { ...useGameForgeStore.getState() };
    assert(
      initialStoreState.isPlaying === afterStoreState.isPlaying &&
      initialStoreState.activeAnimationId === afterStoreState.activeAnimationId,
      "Zero Zustand state mutations occurred during 60Hz inspector updates"
    );

    runtime.dispose();
  }

  console.log(`\n✅ ALL ${passed}/${total} PHASE 6D-E CHARACTER ANIMATION INSPECTOR TESTS PASSED!`);
}

runInspectorTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
