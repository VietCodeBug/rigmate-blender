# RigMate Project Brief

## 1. Product Vision
**RigMate** is an open-source AI assistant embedded directly inside Blender. It empowers content creators, indie game developers, and users with limited 3D rigging expertise to inspect, adjust, and prepare character rigs for real-time game engines.

## 2. Target Pipeline
1. **Generative 3D Creation**: The user generates a 3D character mesh using generative tools (specifically **Tencent Hunyuan 3D**). These models typically have dense topology (~50,000 vertices) and fused or mitten-like hands.
2. **Auto-Rigging**: The model is auto-rigged using **Meshy** (or Mixamo/Tripo) to generate a basic skeleton.
3. **Blender Import**: The rigged asset is imported into Blender.
4. **Assisted Inspection & Refinement with RigMate**:
   - **Mesh Preparation ("Kiểm tra & sửa lưới")**: Context-aware mesh inspection (geometry stats, non-manifold edges, near-duplicates, disconnected components, UV/materials, unweighted vertices, and 4-weight Godot limits) without dogmatic "quality scores".
   - **Character Hand/Finger Remediation**: Disambiguate physical mesh fusion from bone omission or weight leakage; support non-destructive pose testing.
   - **Rig & Transform Verification**: Inspect unapplied transforms, inconsistent scale, and armature modifier bindings.
5. **Target Destination**: Clean export to **Godot Engine** via glTF 2.0 (`.glb`).

## 3. Technical Positioning
- **Not a Text-to-3D Generator**: RigMate does not generate 3D meshes from scratch; it assists with inspection, diagnosis, and guided modification within Blender.
- **Context-Aware Performance Analysis**: A dense vertex count (~50k vertices) is highlighted as a real-time rendering consideration for Godot, not as an intrinsic mesh defect.
- **Non-Destructive Mesh Preparation**: Inspection is strictly read-only; mutations require explicit repair plans, verified pre-mutation checkpoints, and isolated preview copies.
- **Conversational Assistant & MCP Tool Dispatch**: Users interact naturally via the Blender Sidebar tab while AI providers orchestrate safe scene inspection tools via the Model Context Protocol (MCP).
- **English-First Technical Foundation**: All technical internals, comments, error codes, and server logs are standardized in English. Multilingual end-user localization (e.g. Vietnamese) is handled via a dedicated i18n layer.
