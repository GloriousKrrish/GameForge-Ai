import { Box, Grid3x3, RotateCcw, Loader2, Activity } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { useGameForgeStore } from "@/store/useGameForgeStore";
import { AnimationRuntimeManager } from "@/runtime/AnimationRuntimeManager";
import { AnimationClipLoader } from "@/runtime/AnimationClipLoader";

// ── Rig Bone Overlay Helpers ──────────────────────────────────────────────────

interface BoneData {
  id: string;
  name: string;
  parent_id?: string | null;
  head: number[];
  tail: number[];
}

function buildRigOverlay(bones: BoneData[], scene: THREE.Scene): THREE.LineSegments {
  const positions: number[] = [];
  const boneById: Record<string, BoneData> = {};
  for (const b of bones) boneById[b.id] = b;

  for (const bone of bones) {
    // Head → Tail (the bone stick)
    positions.push(...bone.head, ...bone.tail);
    // Tail of parent → Head of child (connector)
    if (bone.parent_id && boneById[bone.parent_id]) {
      const parent = boneById[bone.parent_id];
      positions.push(...parent.tail, ...bone.head);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));

  const material = new THREE.LineBasicMaterial({
    color: 0xd4a853,        // gold
    linewidth: 2,
    depthTest: false,
    transparent: true,
    opacity: 0.85,
  });

  const overlay = new THREE.LineSegments(geometry, material);
  overlay.name = "__rig_overlay__";
  overlay.renderOrder = 999;
  scene.add(overlay);
  return overlay;
}

// ─────────────────────────────────────────────────────────────────────────────

export function Viewport() {
  const [mode, setMode] = useState<"shaded" | "wireframe">("shaded");
  const containerRef = useRef<HTMLDivElement>(null);

  const activeAssetUrl = useGameForgeStore((s) => s.activeAssetUrl);
  const generationStatus = useGameForgeStore((s) => s.generationStatus);
  const objectStats = useGameForgeStore((s) => s.objectStats);
  const setObjectStats = useGameForgeStore((s) => s.setObjectStats);
  const errorMessage = useGameForgeStore((s) => s.errorMessage);
  const activeSkeleton = useGameForgeStore((s) => s.activeSkeleton);
  const isRigVisualized = useGameForgeStore((s) => s.isRigVisualized);
  const setIsRigVisualized = useGameForgeStore((s) => s.setIsRigVisualized);

  const controlsRef = useRef<OrbitControls | null>(null);
  const loadedModelRef = useRef<THREE.Group | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rigOverlayRef = useRef<THREE.LineSegments | null>(null);
  const animationRuntimeRef = useRef<AnimationRuntimeManager>(new AnimationRuntimeManager());
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());
  const clipLoaderRef = useRef<AnimationClipLoader>(new AnimationClipLoader());

  // ── Rig overlay: add / remove when isRigVisualized or activeSkeleton changes ──
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // Remove existing overlay first
    if (rigOverlayRef.current) {
      scene.remove(rigOverlayRef.current);
      rigOverlayRef.current.geometry.dispose();
      (rigOverlayRef.current.material as THREE.Material).dispose();
      rigOverlayRef.current = null;
    }

    if (isRigVisualized && activeSkeleton?.bones?.length) {
      const overlay = buildRigOverlay(activeSkeleton.bones as BoneData[], scene);
      rigOverlayRef.current = overlay;
    }
  }, [isRigVisualized, activeSkeleton]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Setup Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0c10);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(4, 3, 5);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;

    // Clear previous children
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    // 2. Add OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // 3. Add Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xfff5e6, 1.2);
    dirLight1.position.set(5, 10, 7);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x4080ff, 0.4);
    dirLight2.position.set(-5, -2, -5);
    scene.add(dirLight2);

    // 4. Add Grid Helper
    const gridHelper = new THREE.GridHelper(10, 10, 0x4a3b2c, 0x1f2937);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    // 5. Load GLB Asset if available
    if (activeAssetUrl) {
      const loader = new GLTFLoader();
      const targetUrl = activeAssetUrl.startsWith("http")
        ? activeAssetUrl
        : `http://localhost:8000${activeAssetUrl}`;

      loader.load(
        targetUrl,
        (gltf) => {
          if (loadedModelRef.current) {
            scene.remove(loadedModelRef.current);
            animationRuntimeRef.current.unregisterCharacter("active_model");
          }
          const model = gltf.scene;
          loadedModelRef.current = model;

          // Register loaded character root with runtime manager
          animationRuntimeRef.current.registerCharacter("active_model", model);

          // Phase 6D-B: Explicit clip discovery & binding via AnimationClipLoader
          // If GLB contains animation clips, discover, validate, and bind them
          // without auto-playing (playback UI is a later milestone).
          if (gltf.animations && gltf.animations.length > 0) {
            for (let i = 0; i < gltf.animations.length; i++) {
              const clip = gltf.animations[i];
              if (clip && isFinite(clip.duration) && clip.duration > 0 && clip.tracks?.length > 0) {
                const animId = clip.name || `clip_${i}`;
                animationRuntimeRef.current.registerAnimationClip("active_model", animId, clip);
              }
            }
          }

          let meshCount = 0;
          let triCount = 0;

          model.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              meshCount++;
              const mesh = child as THREE.Mesh;
              if (mesh.geometry) {
                triCount += mesh.geometry.index
                  ? mesh.geometry.index.count / 3
                  : mesh.geometry.attributes.position.count / 3;
              }
            }
          });

          setObjectStats({ objects: meshCount, tris: Math.round(triCount) });

          // Center model inside viewport bounds
          const box = new THREE.Box3().setFromObject(model);
          const center = box.getCenter(new THREE.Vector3());
          model.position.sub(center);

          scene.add(model);
        },
        undefined,
        (err) => {
          console.error("Failed to load GLB model in Viewport:", err);
        }
      );
    } else {
      setObjectStats({ objects: 0, tris: 0 });
      animationRuntimeRef.current.unregisterCharacter("active_model");
    }

    // 6. Animation Loop
    let animationFrameId: number;
    clockRef.current.start();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const delta = clockRef.current.getDelta();
      animationRuntimeRef.current.update(delta);

      if (loadedModelRef.current) {
        loadedModelRef.current.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            if (Array.isArray(mesh.material)) {
              mesh.material.forEach((m) => (m.wireframe = mode === "wireframe"));
            } else if (mesh.material) {
              mesh.material.wireframe = mode === "wireframe";
            }
          }
        });
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 7. Handle Resize
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      clipLoaderRef.current.dispose();
      animationRuntimeRef.current.dispose();
      renderer.dispose();
      sceneRef.current = null;
    };
  }, [activeAssetUrl, mode, setObjectStats]);

  const handleResetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  return (
    <section className="relative flex min-w-0 flex-1 flex-col bg-background">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-1">
          {(["shaded", "wireframe"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1.5 text-xs capitalize transition-colors ${
                mode === m
                  ? "bg-gold/10 text-gold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {m}
            </button>
          ))}
          {/* Rig Visualize Toggle */}
          <button
            onClick={() => setIsRigVisualized(!isRigVisualized)}
            id="btn-viewport-rig-vis"
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors ${
              isRigVisualized
                ? "bg-gold/10 text-gold"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title={isRigVisualized ? "Hide Rig Overlay" : "Show Rig Overlay"}
          >
            <Activity className="size-3.5" />
            Rig
          </button>
        </div>
        <button
          onClick={handleResetCamera}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <RotateCcw className="size-3.5" />
          Reset Camera
        </button>
      </div>

      <div className="viewport-grid relative flex flex-1 items-center justify-center overflow-hidden">
        {/* WebGL Canvas Container */}
        <div ref={containerRef} className="absolute inset-0 h-full w-full" />

        {/* Empty State Overlay */}
        {!activeAssetUrl && generationStatus !== "processing" && (
          <div className="pointer-events-none relative z-10 flex flex-col items-center gap-4 text-center">
            <span className="flex size-20 items-center justify-center rounded-xl border border-gold/25 bg-panel/80 text-gold gold-glow backdrop-blur-sm">
              <Box className="size-8" />
            </span>
            <div>
              <h2 className="font-serif text-2xl text-foreground">Empty Workspace</h2>
              <p className="mt-1 max-w-xs text-sm text-muted-foreground">
                Describe a model below (e.g. &quot;Create a red metallic cube&quot;) to begin forging your scene.
              </p>
            </div>
          </div>
        )}

        {/* Processing Loader Overlay */}
        {generationStatus === "processing" && (
          <div className="pointer-events-none relative z-10 flex flex-col items-center gap-3 rounded-xl border border-gold/30 bg-panel/80 p-6 backdrop-blur-md">
            <Loader2 className="size-8 animate-spin text-gold" />
            <p className="text-sm text-gold">Executing Blender BPY Pipeline...</p>
          </div>
        )}

        {/* Error Notification Overlay */}
        {errorMessage && (
          <div className="absolute top-4 z-20 rounded-md border border-destructive bg-destructive/10 px-4 py-2 text-xs text-destructive">
            {errorMessage}
          </div>
        )}

        {/* Rig Overlay Active Badge */}
        {isRigVisualized && (
          <div className="pointer-events-none absolute top-3 right-4 z-10 flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-2.5 py-1 text-[10px] font-semibold text-gold backdrop-blur-sm">
            <Activity className="size-3" />
            Rig Overlay Active
          </div>
        )}

        {/* Bottom Bar Info */}
        <div className="pointer-events-none absolute bottom-3 left-4 flex items-center gap-2 text-[11px] text-muted-foreground">
          <Grid3x3 className="size-3.5" />
          Grid 1m · WebGL Engine
        </div>
        <div className="pointer-events-none absolute bottom-3 right-4 text-[11px] text-muted-foreground">
          {objectStats.objects} objects · {objectStats.tris} tris
        </div>
      </div>
    </section>
  );
}

