import * as THREE from "three";
import { AnimationRuntimeManager } from "./AnimationRuntimeManager";

function createMockCharacterAndClip(): {
  root: THREE.Group;
  clip: THREE.AnimationClip;
} {
  const root = new THREE.Group();
  root.name = "CharacterRoot";

  const bone = new THREE.Bone();
  bone.name = "spine";
  root.add(bone);

  const times = [0, 0.5, 1.0];
  const values = [0, 0, 0, 0, 0.5, 0, 0, 1.0, 0]; // Y translation keyframes
  const track = new THREE.VectorKeyframeTrack("spine.position", times, values);

  const clip = new THREE.AnimationClip("TestWalk", 1.0, [track]);

  return { root, clip };
}

function runTests() {
  console.log("=== RUNNING ANIMATION RUNTIME MANAGER UNIT TESTS ===");
  let passed = 0;
  let total = 0;

  function assert(condition: boolean, message: string) {
    total++;
    if (!condition) {
      console.error(`❌ TEST FAILED: ${message}`);
      throw new Error(`Test failed: ${message}`);
    }
    passed++;
    console.log(`  ✓ ${message}`);
  }

  const manager = new AnimationRuntimeManager();

  // Test 1 — Mixer Creation
  const char1 = createMockCharacterAndClip();
  const mixer1 = manager.registerCharacter("char_1", char1.root);
  assert(manager.hasCharacter("char_1"), "Character 1 registered successfully");
  assert(mixer1 instanceof THREE.AnimationMixer, "Mixer 1 created");
  assert(manager.getMixer("char_1") === mixer1, "Get mixer returns correct instance");

  // Test 2 — Clip Registration & Action Creation
  const action1 = manager.registerAnimationClip("char_1", "anim_walk", char1.clip);
  assert(action1 instanceof THREE.AnimationAction, "AnimationAction created for char_1");

  // Test 3 — Playback Activation
  const playSuccess = manager.play("char_1", "anim_walk");
  assert(playSuccess, "Play returned true");
  assert(manager.isPlaying("char_1"), "Character 1 is playing");

  // Test 4 — Pause Control
  const pauseSuccess = manager.pause("char_1");
  assert(pauseSuccess, "Pause returned true");
  assert(!manager.isPlaying("char_1"), "Character 1 is not playing after pause");

  // Test 5 — Playback Speed Control
  const speedSuccess = manager.setPlaybackSpeed("char_1", 2.0);
  assert(speedSuccess, "setPlaybackSpeed returned true");
  assert(mixer1.timeScale === 2.0, "Mixer timeScale updated to 2.0");

  // Test 6 — Scrub Foundation (setTime)
  manager.play("char_1", "anim_walk");
  const timeSuccess = manager.setTime("char_1", 0.5);
  assert(timeSuccess, "setTime returned true");
  assert(Math.abs(manager.getCurrentTime("char_1") - 0.5) < 0.001, "Current time set to 0.5s");

  // Test 7 — Frame Update Progression
  const spineBone = char1.root.getObjectByName("spine") as THREE.Bone;
  manager.play("char_1", "anim_walk");
  manager.setPlaybackSpeed("char_1", 1.0);
  manager.setTime("char_1", 0.5);
  const updatedY = spineBone.position.y;
  assert(updatedY > 0, `Bone position updated by mixer progression (y=${updatedY})`);

  // Test 8 — Multiple Characters Independence
  const char2 = createMockCharacterAndClip();
  const mixer2 = manager.registerCharacter("char_2", char2.root);
  manager.registerAnimationClip("char_2", "anim_idle", char2.clip);
  manager.play("char_2", "anim_idle");
  assert(manager.hasCharacter("char_1") && manager.hasCharacter("char_2"), "Both characters registered independently");
  assert(mixer1 !== mixer2, "Mixers are distinct per character");

  // Test 9 — Cleanup and Unregistration
  manager.unregisterCharacter("char_1");
  assert(!manager.hasCharacter("char_1"), "Char 1 unregistered");
  assert(manager.hasCharacter("char_2"), "Char 2 remains registered after Char 1 disposal");

  manager.dispose();
  assert(!manager.hasCharacter("char_2"), "All characters cleared on dispose");

  console.log(`\n✅ ALL ${passed}/${total} ANIMATION RUNTIME MANAGER TESTS PASSED SUCCESSFULLY!`);
}

runTests();
