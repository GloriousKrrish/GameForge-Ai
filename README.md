# GameForge AI — Generative 3D Game Engine Platform

GameForge AI is an end-to-end generative 3D engine platform powered by AI planning, controlled execution graphs, headless Blender rigging pipelines, PBR material creation, and real-time Three.js viewport visualization.

## Phase 5 — Characters & Rigging Pipeline

Phase 5 establishes a complete, persistent, animation-ready character foundation:

- **Character Domain**: Asset-linked character management, classifications (`HUMANOID`, `QUADRUPED`, `CREATURE`, `CUSTOM`), and lifecycle state machine (`UNCLASSIFIED` → `CLASSIFIED` → `RIGGING` → `RIGGED` → `SKINNING` → `READY`).
- **Skeleton & Bone Hierarchy**: Deterministic 9-bone humanoid hierarchy with stable bone IDs (`Root`, `Spine`, `Chest`, `Neck`, `Head`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`) and cycle rejection.
- **Headless Blender Rigging**: Controlled BPY execution graph dispatches to system Blender CLI (e.g. Blender 5.2) to create armatures, bind meshes via `ARMATURE` modifiers, calculate distance-weighted vertex groups, and export rigged `.glb` artifacts.
- **GLB Binary Inspection & Weight Validation**: Automated glTF 2.0 container inspection (`glb_inspector.py`) and strict vertex weight normalization validation ($\sum w_i \approx 1.0$).
- **Character UI & Rig Overlay**: Integrated Character Library subtab, PropertiesPanel Character Inspector, and Three.js 3D viewport skeleton bone overlay.

## Development & Testing

### Python Backend & Suite
```sh
# Run pytest backend test suite (78 tests)
python -m pytest backend/tests -v
```

### Frontend Web Application
```sh
# Run dev server
npm run dev

# Production build
npm run build
```

