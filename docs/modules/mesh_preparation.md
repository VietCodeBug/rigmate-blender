# Mesh Preparation Specification ("Kiểm tra & sửa lưới")

**Module Identifier**: `mesh_preparation`  
**Vietnamese UI Name**: `Kiểm tra & sửa lưới`  
**Document Status**: `CANONICAL SPECIFICATION`  
**Technical Standard**: English-first (code identifiers, requirements, tool contracts, error codes, logs)  
**Target Environments**: Blender 4.0+ / 5.2+ (Host Add-on), Godot Engine 4.x (Target Runtime), Headless RigMate Core  

---

## 1. Module Overview & Philosophy

### 1.1 Context
Generative 3D creation tools (such as **Tencent Hunyuan 3D**) produce dense polygon surfaces (~50,000 vertices), frequently auto-rigged by tools like **Meshy** or Mixamo. While such characters can look visually plausible in viewport rendering, their geometric and structural properties often introduce severe blockers for animation, deformation, skin weighting, finger articulation, and real-time game performance in Godot Engine.

The **Mesh Preparation** module empowers users—especially indie game developers and creators with limited 3D technical art experience—to systematically inspect, evaluate, understand, and safely repair meshes before rigging and export.

### 1.2 Core Product Questions
This module directly answers 9 concrete questions for any asset:
1. **Goal Fitness**: Is this mesh suitable for the user's specific intended use (e.g. static prop vs. deforming character)?
2. **Problem Localization**: Which exact regions exhibit geometry, topology, or deformation risks?
3. **Severity Differentiation**: Is a finding merely informational, worthy of manual review, or an actual blocker for the chosen goal?
4. **Evidence Provenance**: Is each finding backed by deterministic geometric measurement or heuristic pattern inference?
5. **Observed Evidence**: What quantitative facts and measurements produced this finding?
6. **Remediation Options**: What repair paths exist (cleanup, decimation, remesh, retopology)?
7. **Downstream Blast Radius**: What data layers could be altered by each remediation?
8. **Data Preservation Guarantees**: Can UVs, material assignments, skin weights, armature hierarchy, shape keys, and silhouette shape be preserved?
9. **Safe Reversibility**: Can the user preview the change on an isolated copy and restore state via verified checkpoints?

### 1.3 Anti-Goals & Architectural Prohibitions
To avoid misleading users and corrupting production pipelines, the Mesh Preparation module strictly adheres to the following principles:
- **NO Uniform "Mesh Quality Score"**: A single scalar score (e.g. "82/100") is ungrounded and misleading. Mesh fitness is strictly contextual to the target use case.
- **NO Dogmatic Quad-Only Doctrine**: Triangles are fully valid in real-time game engines. Triangles on planar surfaces or rigid objects are not errors.
- **NO Vertex Count Dogma**: A 50,000-vertex model is not intrinsically broken; it is evaluated against target Godot platform budgets, LOD strategies, and camera distance.
- **NO Universal Automatic Retopology Fantasy**: Automatic retopology cannot solve every asset; it often destroys hand-tuned UVs, shape keys, and sharp mechanical edges.
- **NO Silent Destructive Operations**: Source assets are NEVER modified without an explicit user-approved repair plan, verified checkpoint, and postcondition verification.

---

## 2. Requirements & Traceability

### 2.1 Functional Requirements (FR-070 – FR-095)

| Requirement ID | Title | Summary Purpose |
| :--- | :--- | :--- |
| **FR-070** | User Goal Selection | User selects a primary goal (`STATIC_OBJECT`, `ANIMATED_CHARACTER`, `HAND_FINGER_REPAIR`, `GODOT_EXPORT_PREPARATION`, `CUSTOM`) governing contextual severity. |
| **FR-071** | Inspection Scope Definition | User specifies target scope (`SELECTED_OBJECT`, `SELECTED_COMPONENT_REGION`, `VERTEX_GROUP`, `WHOLE_CHARACTER`, `AUTO_SUGGESTED_REGION`). |
| **FR-072** | Geometry Statistics Extraction | Computes deterministic vertex count, edge count, polygon count, and triangulated face count without modifying geometry. |
| **FR-073** | Topological Structure Analysis | Inspects non-manifold edges, open boundaries, loose vertices/edges, degenerate faces, and inverted normals. |
| **FR-074** | Disconnected Component Detection | Detects disconnected geometry islands while classifying clothing, accessories, and hair cards as valid multi-part geometry. |
| **FR-075** | Model-Relative Near-Duplicate Detection | Computes near-duplicate vertex clusters using scale-relative bounding-box thresholds rather than fixed millimetre distances. |
| **FR-076** | UV & Material Dependency Inventory | Audits UV map presence, material slots, texture references, missing assets, and distinguishes valid mirrored UVs from defects. |
| **FR-077** | Deformation Readiness Inspection | Audits armature modifiers, vertex groups, unweighted vertices, and flags vertices exceeding Godot's 4-weight skinning limit. |
| **FR-078** | Hand & Finger Geometry Inspection | Heuristically isolates hand regions, detects geometric finger webbing or physical fusion, and evaluates joint ring density. |
| **FR-079** | Hand Landmark Confirmation | Prompts user for interactive landmark confirmation (`NEEDS_INPUT`) when automated finger base/tip confidence is ambiguous. |
| **FR-080** | Configurable Finger Count | Supports humanoid (5-finger) and stylized/cartoon (3 or 4-finger) hand structures via configurable rules. |
| **FR-081** | Hand Defect Categorization | Distinguishes visually touching fingers, geometrically merged meshes, bone chain omissions, and weight painting leakage. |
| **FR-082** | Non-Destructive Test Pose Checks | Executes non-destructive temporary test poses (`EXTENDED`, `FLEX`, `FIST`, `PINCH`, `GRIP`) and verifies restoration to rest pose. |
| **FR-083** | Repair Taxonomy Differentiation | Distinguishes `CLEANUP`, `DECIMATION`, `REMESH`, and `RETOPOLOGY`, presenting clear risk trade-offs for each. |
| **FR-084** | Scoped Repair Plan Generation | Generates typed, inspectable repair plans grouping approved operations, preconditions, and preservation expectations. |
| **FR-085** | Preview on Staging Copy | Executes proposed mutations strictly on temporary duplicate objects/documents without touching live working assets. |
| **FR-086** | Before/After Comparative Metrics | Produces quantitative differential summaries (polycount delta, bounding volume drift, weight variance, UV distortion). |
| **FR-087** | Data Preservation Enforcement | Flags operations that risk UVs, weights, or shape keys with explicit warning banners and requires transfer strategy approval. |
| **FR-088** | Region Reference Invalidation | Enforces `REGION_STALE` on index-dependent selections whenever topology-altering operations change document revision. |
| **FR-089** | Checkpoint Precondition for Apply | Requires verified content-addressed pre-mutation snapshot prior to executing any destructive mesh edit. |
| **FR-090** | Unsaved Live Document Guard | Prompts user (`NEEDS_INPUT`) if live Blender scene has unsaved changes before creating durable file checkpoints. |
| **FR-091** | Contextual Godot Budget Advisory | Evaluates mesh budgets against target hardware platform, LOD tiers, and on-screen character instances. |
| **FR-092** | AI Structured Summary Transmission | Restricts AI provider communication to high-level JSON summaries, statistics, and findings; prohibits transmitting raw vertex arrays. |
| **FR-093** | Blender Main-Thread Isolation | Ensures heavy geometric queries run non-blockingly and dispatch UI updates via thread-safe Blender timer callbacks. |
| **FR-094** | Non-Destructive Restore to Copy | Provides one-click restore from checkpoint materializing `<name>.recovered.<timestamp>.<ext>` without silent live overwrite. |
| **FR-095** | Independent 2D Godot Operation | Ensures all 2D Godot pipelines remain 100% functional even when Blender is absent or mesh modules are disabled. |

### 2.2 Non-Functional Requirements (NFR-020 – NFR-025)

| NFR ID | Category | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-020** | Execution Safety | Read-only inspection tools MUST NEVER acquire write locks or modify document revision under any failure mode. |
| **NFR-021** | Performance & Scalability | Geometry inspection on a 100,000-triangle mesh must complete within 3.0 seconds on standard consumer CPU hardware. |
| **NFR-022** | Memory Footprint | Standalone inspection operations must not allocate more than 2x the base mesh memory buffer during BMesh evaluation. |
| **NFR-023** | Headless Verifiability | All diagnostic rule logic, severity classification, and plan generation must run headlessly in pure Python without `bpy`. |
| **NFR-024** | Localization Integrity | All rule titles, descriptions, recommendations, and impact statements must support localized keys in English and Vietnamese. |
| **NFR-025** | Zero External Addon Leak | Standalone add-on ZIP package must not require external Python packages (`pydantic`, `fastapi`, `mcp`, `numpy`). |

### 2.3 Traceability Matrix

| Requirement | User Story | Tool Contract | Primary Acceptance Criterion |
| :--- | :--- | :--- | :--- |
| **FR-070**, **FR-071** | US-1 | `mesh.inspect`, `mesh.analyze` | A1 (No mutation during inspection) |
| **FR-072**, **FR-073** | US-1, US-4 | `mesh.inspect` | A1, A18 (Triangle vs polygon distinguished) |
| **FR-074** | US-3 | `mesh.inspect`, `mesh.plan_repair` | A2 (Clothing/hair islands not auto-deleted) |
| **FR-075** | US-1 | `mesh.inspect` | A1 (Model-relative near-duplicate thresholds) |
| **FR-076** | US-8 | `mesh.inspect` | A8 (UV preservation warning) |
| **FR-077** | US-2 | `mesh.inspect`, `mesh.analyze` | A11 (Weight vs geometry distinction) |
| **FR-078**, **FR-079** | US-2 | `mesh.inspect`, `mesh.analyze` | A11, A12 (Landmarks prompt when ambiguous) |
| **FR-080**, **FR-081** | US-2 | `mesh.inspect`, `deformation.run_pose_checks` | A11, A12 (Configurable finger counts) |
| **FR-082** | US-2 | `deformation.run_pose_checks` | A1 (Rest pose verified restored) |
| **FR-083**, **FR-084** | US-5 | `mesh.plan_repair` | A17 (Grouped plan approval) |
| **FR-085**, **FR-086** | US-5 | `mesh.preview_repair`, `mesh.compare` | A3, A20 (Working source untouched in preview) |
| **FR-087** | US-8 | `mesh.plan_repair`, `mesh.apply_repair` | A8, A9, A10 (Preservation failure alerts) |
| **FR-088** | US-6 | `mesh.apply_repair` | A5, A18 (Stale region references rejected) |
| **FR-089**, **FR-090** | US-5, US-7 | `mesh.apply_repair`, `operation.restore_checkpoint` | A6, A7, A19 (Checkpoint required & verified) |
| **FR-091** | US-4 | `mesh.analyze` | A14 (Contextual Godot budget) |
| **FR-092** | US-1 | `mesh.inspect`, `mesh.analyze` | A1 (Zero raw coordinate arrays to LLM) |
| **FR-093** | US-1 | Host Adapter Protocol | A13 (Blender UI responsiveness) |
| **FR-094** | US-5 | `operation.restore_checkpoint` | A7 (Non-destructive restore-to-copy) |
| **FR-095** | US-4 | Core Package Architecture | A15 (2D Godot independence from Blender) |

---

## 3. User Stories

### US-1: Safe Non-Destructive Inspection (Beginner Creator)
> **As a** beginner 3D character creator,  
> **I want to** run a comprehensive diagnostic inspection on my imported model without modifying any geometry,  
> **So that** I can understand whether it is ready for rigging and game export without fear of breaking my asset.

### US-2: Hand & Finger Root-Cause Isolation (Character Rigger)
> **As a** character creator with a generative AI mesh,  
> **I want** hand and finger issues separated into physical geometry defects versus skin weighting or bone omissions,  
> **So that** I do not waste hours rebuilding hand topology when the actual issue is missing finger weights or bone bindings.

### US-3: Multi-Part Asset Protection (Stylized Artist)
> **As a** character artist with separate clothing, hair cards, and accessory meshes,  
> **I want** disconnected geometry components reported with semantic context rather than automatically deleted,  
> **So that** valid detached character elements are safely preserved.

### US-4: Contextual Game Budgeting (Indie Game Developer)
> **As an** indie game developer preparing assets for Godot Engine,  
> **I want** geometry budget advice based on my target platform and scene instance count rather than an arbitrary universal polycount cap,  
> **So that** I optimize meshes only when necessary for my target runtime performance.

### US-5: Transparent Preview & Safe Reversibility (Pipeline Technical Artist)
> **As a** pipeline artist applying automated cleanup,  
> **I want to** preview proposed repairs on an isolated copy and have a guaranteed checkpoint rollback path,  
> **So that** I can visually inspect geometry changes and revert instantly if an automated operation creates unwanted artifacts.

### US-6: Stale Selection Invalidation (Cautious Animator)
> **As a** user editing specific sub-regions of a mesh,  
> **I want** old vertex and face selection IDs invalidated immediately when any operation changes mesh topology,  
> **So that** subsequent repair tools cannot accidentally operate on wrong vertices or corrupt neighboring surfaces.

### US-7: Robust Connection Drop Recovery (Remote / Laptop Creator)
> **As a** user working over an IPC socket or local network,  
> **I want** RigMate to query durable host execution status after a disconnect or crash before deciding to retry,  
> **So that** network drops never cause a mesh mutation to be executed twice.

### US-8: Downstream Data Layer Preservation Warning (3D Generalist)
> **As a** 3D generalist whose character already has UVs, materials, and shape keys,  
> **I want** clear advance warnings whenever an operation cannot guarantee preservation of these data layers,  
> **So that** I never approve an automated retopology or remesh that silently destroys my facial blendshapes or texture mapping.

---

## 4. User Experience & Checkbox UI Flow

The user interface in the Blender Sidebar tab (`N` panel > RigMate > **Kiểm tra & sửa lưới**) follows a 5-step progressive disclosure flow:

```text
+-------------------------------------------------------------------------+
|                  RIGMATE - KIỂM TRA & SỬA LƯỚI (MESH PREPARATION)       |
+-------------------------------------------------------------------------+
| STEP A: PURPOSE (Mục đích sử dụng)                                      |
|   (o) Nhân vật hoạt hình (Animated Character)                           |
|   ( ) Vật thể tĩnh (Static Prop / Environment)                          |
|   ( ) Sửa bàn tay & ngón tay (Hand & Finger Repair)                     |
|   ( ) Chuẩn bị xuất Godot (Godot Export Preparation)                    |
|   ( ) Tùy chỉnh (Custom Profile...)                                     |
+-------------------------------------------------------------------------+
| STEP B: SCOPE (Phạm vi đối tượng)                                       |
|   [x] Đối tượng đang chọn (Selected Object: "Character_Mesh")           |
|   [ ] Vùng đỉnh / mặt đang chọn (Selected Sub-mesh Region)              |
|   [ ] Nhóm đỉnh (Vertex Group) -> [ Dropdown: All ]                     |
|   [ ] Toàn bộ nhân vật (Whole Character Hierarchy)                      |
|   [!] Vùng tự động đề xuất (Suggested Region) [Disabled: No scan yet]   |
+-------------------------------------------------------------------------+
| STEP C: INSPECTION CHECKS (Hạng mục kiểm tra)                           |
|   [x] Thống kê hình học cơ bản (Geometry Statistics)                    |
|   [x] Cấu trúc lưới & Non-manifold (Structural Topology)                |
|   [x] UV, Vật liệu & Texture (UV & Material Integrity)                  |
|   [x] Sẵn sàng biến dạng & Bone Weights (Deformation Readiness)         |
|   [ ] Kiểm tra chi tiết ngón tay (Hand / Finger Deep Scan)              |
|   [x] Đánh giá ngân sách Godot (Godot Budget Assessment)                |
|                                                                         |
|   [  NÚT: CHẠY KIỂM TRA (RUN INSPECTION)  ] (Không sửa đổi file)        |
+-------------------------------------------------------------------------+
| STEP D: FINDINGS & DIAGNOSIS (Kết quả phát hiện)                        |
|   [!] 2 LỖI CHẶN (BLOCKERS) | [?] 3 CẦN XEM LẠI | [i] 4 THÔNG TIN       |
|                                                                         |
|   [x] BLK-01: Non-manifold edges tại khớp khuỷu tay (Elbow Joint)       |
|       Tác động: Gây rách lưới khi uốn cong tay.                         |
|       [Xem vùng lỗi] [Đưa vào kế hoạch sửa]                             |
|                                                                         |
|   [x] BLK-02: Đỉnh chưa gán trọng số (38 unweighted vertices)           |
|       Tác động: Đỉnh sẽ bị văng về gốc tọa độ khi chuyển động.          |
|       [Xem vùng lỗi] [Đưa vào kế hoạch sửa]                             |
|                                                                         |
|   [ ] WRN-01: Mật độ lưới cao (52,400 tris > 30k đề xuất cho Mobile)    |
|       Tác động: Giảm FPS trên thiết bị di động yếu.                     |
|       [Đưa vào kế hoạch sửa]                                            |
+-------------------------------------------------------------------------+
| STEP E: PLAN, PREVIEW & REPAIR (Kế hoạch & Sửa chữa an toàn)            |
|   [ Nút: Tạo Kế Hoạch Sửa (Create Plan) ]                               |
|   -> Kế hoạch #PLN-104: 2 mục sửa | Checkpoint: Bắt buộc | UV: Giữ     |
|                                                                         |
|   [ Nút: Xem Trước Trên Bản Sao (Preview on Copy) ]                     |
|   -> Đã tạo đối tượng tạm: "Character_Mesh_Preview"                     |
|                                                                         |
|   [ Nút: Áp Dụng Thay Đổi (Apply Changes) ] (Ghi Checkpoint & Lock)     |
|   [ Nút: Khôi Phục Bản Lưu (Restore Checkpoint) ]                       |
+-------------------------------------------------------------------------+
```

### UI Interaction Invariants:
1. **Primary Purpose Single-Select**: Step A uses a single-select radio group to establish primary contextual severity. Secondary constraints (e.g. Godot target) are configured in Step C.
2. **Explicit Disabled Explanations**: When a scope in Step B is unavailable, a clear badge is displayed:
   - `NO_MESH_SELECTED`: Active selection is not a Mesh object.
   - `NO_COMPONENT_SELECTION`: Mesh is in Object Mode with no active sub-element selection.
   - `NO_VERTEX_GROUP`: Selected mesh possesses 0 vertex groups.
   - `BLENDER_NOT_CONNECTED`: Bridge client is not connected to active Blender instance.
3. **Inspection != Repair Authorization**: Ticking a check in Step C authorizes ONLY measurement and reporting. It NEVER authorizes automatic mutation.
4. **Grouped Plan Review**: Step E presents a holistic plan summary (affected data, preservation outlook, checkpoint ID) rather than prompting modal confirmations for every individual vertex edit.

---

## 5. Canonical Finding Schema

Every diagnostic result produced by the inspection pipeline adheres to a deterministic schema:

```json
{
  "finding_id": "find_mesh_topo_001",
  "rule_id": "RULE-TOPO-NON-MANIFOLD",
  "title": "Non-manifold edges detected in deforming joint",
  "object_id": "obj_character_mesh_01",
  "region_id": "reg_elbow_left_v1",
  "severity": "BLOCKS_SELECTED_GOAL",
  "confidence_class": "DETERMINISTIC",
  "deterministic_or_heuristic": "DETERMINISTIC",
  "evidence": {
    "non_manifold_edge_count": 14,
    "wire_edges": 0,
    "boundary_edges": 14,
    "multi_face_edges": 0,
    "sample_vertex_indices": [1024, 1025, 1032],
    "bounding_box_center": [-0.42, 0.12, 1.35]
  },
  "practical_impact": "Faces will tear open during elbow flexion animations in Godot.",
  "recommended_actions": [
    {
      "action_type": "CLEANUP",
      "tool": "mesh.plan_repair",
      "operation": "fill_boundary_hole",
      "description": "Bridge open edge loops preserving joint boundary loops."
    }
  ],
  "possible_side_effects": "UV coordinates for filled faces must be mapped to avoid texture stretching.",
  "affected_data_types": ["GEOMETRY", "UV_MAPS"],
  "view_region_action": "VIEW3D_OT_rigmate_focus_region",
  "select_for_plan": true
}
```

### Contextual Severity Levels:
- **`INFO`**: Descriptive metric or non-detrimental property (e.g. quad count, presence of mirrored UV islands, clothing detachment).
- **`REVIEW`**: Geometric condition requiring human artistic discretion (e.g. polycount exceeds mobile recommendations, minor non-planar faces).
- **`BLOCKS_SELECTED_GOAL`**: Fatal defect that guarantees failure for the active goal (e.g. unweighted vertices in `ANIMATED_CHARACTER`, degenerate zero-area faces in `GODOT_EXPORT_PREPARATION`).

---

## 6. Scope Model & Region Revision Invalidation

### 6.1 Region Reference Contract
When an inspection flags a localized defect or the user selects a component subset, a **Region Reference** is created:

```python
@dataclass
class MeshRegionReference:
    region_id: str                      # Unique UUID (e.g. "reg_wrist_l_01")
    object_id: str                      # Target Blender object ID
    source_revision: int                # Document revision when region was captured
    selection_kind: str                 # "COMPONENT_INDICES", "BOUNDING_BOX", "VERTEX_GROUP"
    vertex_indices: Optional[List[int]] # Valid ONLY while revision == source_revision
    face_indices: Optional[List[int]]   # Valid ONLY while revision == source_revision
    bounding_box_min: List[float]       # Spatial fallback anchor [x, y, z]
    bounding_box_max: List[float]       # Spatial fallback anchor [x, y, z]
    semantic_label: Optional[str]       # "hand.l", "elbow.r", "eye.l"
```

### 6.2 Region Invalidation Rule (`REGION_STALE`)
1. **Immutable Revision Binding**: A region created at document revision $N$ is strictly tied to revision $N$.
2. **Topology Invalidation**: Any topology-altering mutation (e.g. merging vertices, deleting faces, filling holes, decimation, remeshing) increments document revision to $N+1$.
3. **Index Rejection**: Under revision $N+1$, any operation attempting to reference `vertex_indices` or `face_indices` from revision $N$ is immediately aborted with error code `REGION_STALE`.
4. **Spatial Re-anchoring**: To re-evaluate a stale region under revision $N+1$, the system must either re-run the inspection rule or re-project selection bounds using spatial bounding metadata (`bounding_box_min/max`).

---

## 7. Inspection Rule Catalog

| Rule ID | Rule Name | Category | Method | Evidence Collected | Default Severity (`ANIMATED_CHARACTER`) | Limitations & False Positive Protection |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RULE-STAT-01** | Poly & Triangle Counts | Statistics | Deterministic | Vertex, edge, face, and triangulated triangle counts. | `INFO` | High tri counts are not errors; evaluated against game budgets. |
| **RULE-TOPO-01** | Non-Manifold Edges | Topology | Deterministic | Edges with $\ne 2$ connected faces (wire edges, fan edges). | `BLOCKS_SELECTED_GOAL` | Boundary edges on open neck/eyeball sockets are exempted if intentional. |
| **RULE-TOPO-02** | Loose Geometry | Topology | Deterministic | Isolated vertices and edges with 0 connected faces. | `REVIEW` | Floating vertices provide zero visual value and waste draw calls. |
| **RULE-TOPO-03** | Degenerate Faces | Topology | Deterministic | Faces with zero surface area or collinear vertices. | `BLOCKS_SELECTED_GOAL` | Degenerate faces cause division-by-zero crashes in renderers. |
| **RULE-TOPO-04** | Near-Duplicate Vertices | Topology | Deterministic | Vertex pairs closer than model-relative threshold $\epsilon$. | `REVIEW` | Scale-relative: $\epsilon = 0.0005 \times \text{bbox\_diagonal}$. |
| **RULE-TOPO-05** | Inverted Face Normals | Topology | Deterministic | Faces whose normal vectors conflict with neighbor winding. | `BLOCKS_SELECTED_GOAL` | Causes backface culling transparency holes in Godot. |
| **RULE-STRUC-01** | Disconnected Islands | Structure | Deterministic | Graph traversal counting independent closed sub-meshes. | `INFO` / `REVIEW` | Hair cards, buttons, shoes, and clothing layers are preserved as valid. |
| **RULE-STRUC-02** | Boundary Holes | Structure | Deterministic | Perimeter loops of boundary edges. | `REVIEW` | Distinguishes intentional eye/mouth sockets from accidental holes. |
| **RULE-STRUC-03** | Self-Intersections | Structure | Heuristic | Intersecting face bounding boxes and ray-triangle hits. | `REVIEW` | Clothing intersecting body is flagged for review, not auto-deleted. |
| **RULE-UV-01** | UV Map Missing | UV / Mat | Deterministic | Absence of active UV coordinate layer on mesh. | `BLOCKS_SELECTED_GOAL` | Asset cannot be textured in game engine without UV coordinates. |
| **RULE-UV-02** | UV Island Overlap | UV / Mat | Deterministic | Intersecting UV polygons outside unit tile bounds. | `INFO` / `REVIEW` | Mirrored character UVs (left/right symmetric overlap) are classified valid. |
| **RULE-UV-03** | Missing Texture Ref | UV / Mat | Deterministic | Material image nodes pointing to missing disk paths. | `REVIEW` | Missing textures result in fallback magenta rendering in Godot. |
| **RULE-DEFRM-01** | Armature Mod Missing | Deformation | Deterministic | Mesh object lacks `ARMATURE` modifier. | `BLOCKS_SELECTED_GOAL` | Character cannot animate in game engine without modifier binding. |
| **RULE-DEFRM-02** | Unweighted Vertices | Deformation | Deterministic | Vertices with total bone influence weight $< 0.001$. | `BLOCKS_SELECTED_GOAL` | Causes unweighted vertices to stay pinned to world origin during animation. |
| **RULE-DEFRM-03** | Excessive Bone Weights| Deformation | Deterministic | Vertices influenced by $> 4$ deform bones. | `REVIEW` | Godot standard 3D rendering supports up to 4 weights per vertex (or 8 with extra cost). |
| **RULE-DEFRM-04** | Joint Ring Density | Deformation | Heuristic | Edge loop count around knees, elbows, shoulders. | `REVIEW` | Joints require at least 3 edge loops to bend smoothly without collapsing. |
| **RULE-HAND-01** | Fused Finger Geometry | Hand/Finger | Heuristic | Bridged geometry spans between adjacent finger digits. | `BLOCKS_SELECTED_GOAL` | Fingers cannot articulate independently if vertices are physically shared. |
| **RULE-BUDGET-01** | Godot Engine Budget | Game Budget | Heuristic | Triangle and material count vs. platform target. | `REVIEW` | Evaluates against target device (Mobile: 30k, PC: 100k) and camera distance. |

---

## 8. Hand & Finger Priority Workflow

Because AI-generated characters from Hunyuan 3D frequently suffer from mitten hands, webbed digits, or fused finger geometry, RigMate establishes a dedicated 10-step character hand remediation pipeline:

```text
  [1. Detect Candidate Hand Region]
                 |
  [2. Confidence < 85% ?] ---> YES ---> [Prompt User for Landmark Confirmation (NEEDS_INPUT)]
                 |                                      |
                 +<-------------------------------------+
                 v
  [3. Inspect Finger Mesh Geometry (Webbing, Fused Vertices)]
                 |
  [4. Inspect Existing Hand / Finger Bones]
                 |
  [5. Inspect Vertex Group Weight Distributions]
                 |
  [6. Problem Classification (Disambiguate Root Cause)]
         |----------------------------------------------------------+
         v                                                          v
   GEOMETRIC DEFECT                                          RIGGING / WEIGHT DEFECT
   - FINGERS_GEOMETRICALLY_MERGED                            - FINGERS_TOUCHING_VISUALLY
   - INSUFFICIENT_JOINT_GEOMETRY                             - WEIGHTS_CAUSE_FINGER_MERGING
         |                                                   - FINGER_BONE_CHAIN_MISSING
         v                                                   - FINGER_WEIGHT_GROUP_MISSING
  [7. Recommend Scoped Repair Plan (Mesh Cut / Separate)]           |
         |                                                          v
         |                                           [Recommend Bone & Weight Repair]
         +--------------------------+-------------------------------+
                                    v
                 [8. Preview Proposed Geometry / Weights on Copy]
                                    |
                 [9. Non-Destructive Test Pose Checks]
                     - EXTENDED
                     - INDIVIDUAL_FINGER_FLEX
                     - FIST
                     - PINCH
                     - OBJECT_GRIP
                                    |
                 [10. Generate Verified Evidence Report]
```

### 8.1 Hand Problem Classification Taxa
- **`FINGERS_TOUCHING_VISUALLY`**: Meshes are physically separated by distinct boundaries; vertices are merely in close spatial proximity. (Fix: Pose adjustment or weight painting, NOT geometric cutting).
- **`FINGERS_GEOMETRICALLY_MERGED`**: Adjacent finger digits share continuous polygonal faces or shared vertices. (Fix: Scoped mesh incision / separation required).
- **`WEIGHTS_CAUSE_FINGER_MERGING`**: Geometry is physically clean, but index finger vertex group has non-zero weights on middle finger vertices. (Fix: Skin weight pruning / re-normalization).
- **`INSUFFICIENT_GEOMETRY_AT_JOINT`**: Finger digits contain only 1 segment or lack intermediate knuckle edge loops. (Fix: Bounded local loop subdivision).
- **`FINGER_BONE_CHAIN_MISSING`**: Armature ends at wrist/hand bone without individual phalange chains. (Fix: Auto-generate finger bone hierarchy).
- **`FINGER_WEIGHT_GROUP_MISSING`**: Finger bones exist but corresponding vertex groups are missing from mesh. (Fix: Generate vertex groups and bind).
- **`CUSTOM_FINGER_COUNT`**: Character hand intentionally features 3 or 4 fingers (e.g. stylized cartoon character). Configurable setting prevents false-positive warnings.

---

## 9. Repair Taxonomy & Preservation Matrix

### 9.1 Repair Classification
1. **`CLEANUP` (Low Risk)**: Surgical repairs operating on discrete defective elements (e.g. deleting floating vertices, filling small planar holes, recalculating inverted normals). Topology indices are mostly preserved; vertex groups, skin weights, and UVs remain intact.
2. **`DECIMATION` (Medium Risk)**: Controlled polygon reduction (e.g. quadric edge collapse). UV coordinates are preserved with minor drift; vertex IDs are re-indexed; skin weights require local re-interpolation.
3. **`REMESH` (High Risk)**: Complete voxel or surface reconstruction. Vertex topology is 100% destroyed. All vertex groups, skin weights, UV unwraps, and shape keys are invalidated and require post-operation transfer/rebaking.
4. **`RETOPOLOGY` (High Risk / Advanced)**:
   - **`LOCAL_RETOPOLOGY`**: Targeted re-meshing of a specific sub-region (e.g. rebuild elbow joint or separate fingers) while sewing boundaries back to the base mesh.
   - **`BROAD_RETOPOLOGY`**: Whole-asset quadrilateral flow generation. Requires advanced external algorithms, shape projection, and complete data transfer. (Research status).

### 9.2 Data Preservation Matrix

| Operation Category | UV Maps | Material Slots | Texture Refs | Vertex Groups | Skin Weights | Armature Mod | Shape Keys | Custom Attrs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Inspection (`mesh.inspect`)** | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` |
| **Cleanup: Remove Loose Verts** | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` |
| **Cleanup: Fix Inverted Normals** | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` | `PRESERVED` |
| **Cleanup: Fill Small Holes** | `TRANSFER_REQUIRED` (new faces) | `PRESERVED` | `PRESERVED` | `LIKELY_PRESERVED` | `TRANSFER_REQUIRED` (new verts) | `PRESERVED` | `LIKELY_PRESERVED` | `UNKNOWN` |
| **Decimation (Edge Collapse)** | `LIKELY_PRESERVED` | `PRESERVED` | `PRESERVED` | `TRANSFER_REQUIRED` | `TRANSFER_REQUIRED` | `PRESERVED` | `INVALIDATED` | `INVALIDATED` |
| **Local Retopology (Scoped)** | `TRANSFER_REQUIRED` | `PRESERVED` | `PRESERVED` | `TRANSFER_REQUIRED` | `TRANSFER_REQUIRED` | `PRESERVED` | `INVALIDATED` | `INVALIDATED` |
| **Surface Remesh (Voxel/Quad)** | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `PRESERVED` | `INVALIDATED` | `INVALIDATED` |
| **Broad Auto-Retopology** | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `INVALIDATED` | `PRESERVED` | `INVALIDATED` | `INVALIDATED` |

---

## 10. Proposed Tool Contracts

The Mesh Preparation module introduces 8 structured tool contracts operating within the existing RigMate execution lifecycle:

### 10.1 `mesh.inspect` (Read-Only)
- **Execution Mode**: `INSPECT` (Read-Only, zero mutation, zero locks, zero checkpoints).
- **Request Parameters**:
  - `project_id: str`
  - `document_id: str`
  - `object_id: str`
  - `goal: str` (`STATIC_OBJECT`, `ANIMATED_CHARACTER`, etc.)
  - `requested_checks: List[str]`
  - `scope: Optional[MeshRegionReference]`
- **Response Payload**:
  - `inspection_id: str`
  - `document_revision: int`
  - `statistics: MeshStatistics`
  - `findings: List[Finding]`
  - `warnings: List[str]`
  - `unsupported_checks: List[str]`

### 10.2 `mesh.analyze` (Read-Only)
- **Execution Mode**: `INSPECT` (Read-Only).
- **Request Parameters**: Consumes `mesh.inspect` output, active goal, and target game engine settings.
- **Response Payload**: Goal-classified findings, confidence scores, practical impact summaries, and recommended repair actions.

### 10.3 `mesh.plan_repair` (Planning)
- **Execution Mode**: `INSPECT` (Read-Only, produces plan).
- **Request Parameters**: `document_id`, `source_revision`, `selected_finding_ids`, `repair_strategy`.
- **Response Payload**: `PreparedPlan` including plan ID, target operations, preconditions, required checkpoint flag, expected data preservation matrix, and postcondition verification criteria.

### 10.4 `mesh.preview_repair` (Safe Staging Mutation)
- **Execution Mode**: `PREVIEW` (Operates exclusively on a duplicate temporary object `obj_name + "_preview"`).
- **Request Parameters**: `plan_id`, `source_object_id`.
- **Response Payload**: `preview_object_id`, before/after comparison metrics, preservation delta report, and temporary object lifecycle token.

### 10.5 `mesh.apply_repair` (High-Risk Mutation)
- **Execution Mode**: `APPLY` (Governed by JobService lifecycle).
- **Invariants**:
  1. Valid `prepared_plan_ref` matching document and revision.
  2. Verified `checkpoint_ref` completed prior to execution.
  3. Single-writer document lock acquired.
  4. Unique `idempotency_key` and canonical request hash.
  5. Postcondition verification via `HostVerificationResult`.
  6. Final receipt persistence.

### 10.6 `mesh.compare` (Read-Only)
- **Execution Mode**: `INSPECT`.
- **Request Parameters**: `source_object_id`, `target_object_id`.
- **Response Payload**: Polycount delta, surface Hausdorff distance, volume difference, UV island drift percentage, and weight variance.

### 10.7 `deformation.run_pose_checks` (Test Posing)
- **Execution Mode**: `INSPECT` with temporary pose evaluation.
- **Invariants**: Applies test poses (`EXTENDED`, `FLEX`, `FIST`, `PINCH`, `GRIP`) in memory or evaluated depsgraph; verifies 100% restoration to rest pose before returning. Permanent user animation channels MUST NEVER be altered.

### 10.8 `operation.restore_checkpoint` (Recovery)
- **Execution Mode**: `RECOVERY`.
- **Invariants**: Reuses existing RigMate CheckpointEngine. Restores snapshot blobs to verified non-destructive copy (`<name>.recovered.<timestamp>.<ext>`) without overwriting active scene files.

---

## 11. Checkpoint, Recovery & Dirty Scene Policy

### 11.1 Checkpoint Binding
Every mutation-capable mesh repair job requires a verified pre-mutation checkpoint binding:
- `project_id`
- `document_id`
- `source_revision`
- `operation_id`
- `job_id`

### 11.2 Dirty Blender Document Invariant
Blender scenes frequently exist in an unsaved in-memory state (`bpy.data.is_dirty == True`). An on-disk `.blend` file may not match the active viewport geometry.
- **Conservative Safety Rule**: If a mutation job requires a durable filesystem checkpoint and the active Blender document contains unsaved changes:
  1. The operation MUST NOT silently snapshot the stale on-disk `.blend` file.
  2. Job transitions to `NEEDS_INPUT`.
  3. UI prompts the user: *"The active Blender scene has unsaved changes. Please save the file (Ctrl+S) or authorize an explicit working snapshot before applying mesh repairs."*
  4. Execution halts until user saves or authorizes snapshot.

---

## 12. AI Data & Privacy Policy

To protect user IP, comply with local-first principles, and avoid token exhaustion, RigMate enforces strict AI payload boundaries:
1. **NO Raw Vertex Dumps**: Arrays of 3D vertex coordinates, edge indices, and face winding lists are NEVER transmitted over the wire to an AI provider.
2. **Local Deterministic Compute**: All geometric algorithms (BMesh queries, manifold checks, duplicate detection, normal verification) execute 100% locally on the user's machine in Blender/Python.
3. **Structured Context Summaries**: The AI provider receives ONLY high-level structured diagnostics:
   - Polycount statistics (e.g. "52,400 triangles")
   - Finding identifiers and titles
   - Affected region labels (e.g. "Elbow_L", "Finger_Index_R")
   - Summary bounding-box metrics
4. **Opt-in Screenshot Assistance**: Viewport screenshots are transmitted ONLY when explicitly permitted by user configuration for visual landmark guidance.

---

## 13. Godot Preparation & 2D Workflow Invariant

### 13.1 Contextual Game Budget Evaluation
Godot game geometry advice is contextual, not an arbitrary cap:
- **Mobile / Web Target**: Recommends $\le 30,000$ triangles per character.
- **Desktop / Console Target**: Recommends $\le 100,000$ triangles per hero character.
- **Crowd / NPC Target**: Recommends $\le 10,000$ triangles with LOD generation.
- **Weight Influences**: Strictly flags vertices with $> 4$ deform bone influences, as Godot's default `StandardMaterial3D` and mesh skinning pipeline optimize for 4 weights per vertex.

### 13.2 2D Godot Workflow Invariant
RigMate's 2D Godot companion workflows (e.g. 2D sprite deformation, Cutout animation, Godot 2D skeleton setup) are **100% architecturally decoupled from 3D Mesh Preparation**:
- 2D Godot projects MUST NEVER require Blender installation.
- 2D workflows MUST NEVER fail or raise warnings if 3D mesh modules are uninstalled or disabled.
- The 2D pipeline executes standalone in Godot without external host dependencies.

---

## 14. Phased Delivery Roadmap

```text
Phase A: Read-Only Inspection  -->  Phase B: Controlled Cleanup  -->  Phase C: Character Hands
(v0.1.5 / v0.2 Baseline)            (v0.2.5 Safe Repair)             (v0.3 Specialized)
- Stats & Topology audit           - Isolated Preview copy          - Hand/finger detection
- UV/Material inventory            - Single-element cleanup         - Landmark confirmation
- Weight/Deform inventory          - Compare metrics                - Weight vs geo split
- Goal-aware severity              - Restore-to-copy                - Non-destructive poses
        |                                  |                                |
        v                                  v                                v
Phase D: Advanced Topology     --------------------------------->   Phase E: Broad Research
(v0.4 Local Remesh)                                                 (v1.0 Auto-Retopology)
- Scoped local retopology                                           - Whole-mesh auto retopo
- Data transfer engines                                             - External engine audit
- Surface deviation metrics                                         - Benchmark test suite
```

### Phase Details:
- **Phase A (Inspection - Priority 1)**: Pure read-only inspection. Provides high value immediately with zero mutation risk. Runs headlessly in test suite with fixture character meshes.
- **Phase B (Controlled Cleanup - Priority 2)**: Introduces preview-on-copy, verified checkpoints, and surgical cleanups (loose verts, inverted normals, small holes).
- **Phase C (Character Hands & Deformation - Priority 3)**: Implements candidate hand isolation, 7-class defect taxonomy, landmark confirmation, and test pose checking.
- **Phase D (Advanced Topology & Data Transfer - Priority 4)**: Scoped local retopology and automated UV/weight transfer algorithms.
- **Phase E (Research & Broad Retopology - Priority 5)**: Comprehensive quad retopology backends. Backends must be evaluated for license compatibility, cross-platform stability, and redistribution rights before adoption.

---

## 15. Acceptance Matrix

| Case ID | Invariant Test Condition | Expected Behavior |
| :--- | :--- | :--- |
| **A1** | Run full inspection on character asset. | Document revision unchanged; zero disk writes; working mesh untouched. |
| **A2** | Inspect mesh with detached clothing/accessories. | Disconnected islands reported with label; NO automatic deletion. |
| **A3** | Create preview copy, then cancel inspection. | Temporary preview object deleted; source mesh 100% identical to original. |
| **A4** | Apply scoped repair targeting Region A. | Vertices outside Region A bounds are verified untouched by postcondition audit. |
| **A5** | Topology edit increments revision $N \to N+1$. | Subsequent attempt to query region from revision $N$ raises `REGION_STALE`. |
| **A6** | Network drops after host apply but before ACK. | Recovery queries durable host status; receives `EXECUTED`; skips duplicate apply. |
| **A7** | Crash recovery triggered on aborted job. | `restore_checkpoint` creates non-destructive `<name>.recovered.<ts>.<ext>` copy. |
| **A8** | Hole filling operation affects UV boundaries. | User receives explicit warning that newly generated faces require UV unwrapping. |
| **A9** | Decimation applied to skinned character. | User receives explicit warning that skin weights require re-interpolation. |
| **A10** | Remesh proposed on mesh with facial shape keys. | UI flags `SHAPE_KEYS_AT_RISK` and blocks apply unless user authorizes transfer. |
| **A11** | Analyze fixture with touching fingers vs merged mesh. | Touching fingers classified as `FINGERS_TOUCHING_VISUALLY`; merged as `FINGERS_GEOMETRICALLY_MERGED`. |
| **A12** | Inspect stylized 4-finger cartoon character. | Setting `expected_fingers_per_hand = 4` suppresses missing 5th finger warning. |
| **A13** | Run inspection in headless CI environment. | Report explicitly marks Blender live runtime evidence as `UNVERIFIED_RUNTIME`. |
| **A14** | Evaluate asset for Godot export. | Distinction maintained between Blender export readiness vs real Godot runtime import. |
| **A15** | Run RigMate in 2D Godot project without Blender. | 2D tooling initializes cleanly with zero Blender dependencies. |
| **A16** | Execute read-only `mesh.inspect` or `mesh.analyze`. | Tools execute immediately without prompting for modal confirmation dialogs. |
| **A17** | User reviews Step E repair plan. | Single grouped authorization covers entire plan; no repetitive low-level prompts. |
| **A18** | Remesh alters vertex indices from 0..5000 to 0..2200. | System rejects stale index lookups and requires spatial bounding re-anchoring. |
| **A19** | Host returns `NOT_FOUND` after crash-before-apply. | JobService verifies same op ID, checkpoint, and lock, then safely redispatches once. |
| **A20** | Inspect or preview an asset with read-only permissions. | Source asset permissions and timestamps remain completely unaltered. |

---

## 16. Test Fixture Backlog

To support headless automated verification, RigMate defines a comprehensive test fixture backlog:

1. `clean_static_mesh.json`: Baseline cube/sphere with manifold topology, clean UVs, zero unapplied transforms.
2. `valid_disconnected_clothing.json`: Character body with detached jacket, boots, and hair card islands.
3. `loose_vertex_noise.json`: High-poly scan containing 25 floating vertices and 10 wire edges.
4. `near_duplicate_vertices.json`: Seam where vertices share near-identical coordinates ($\Delta < 0.0001$).
5. `open_boundary_intentional.json`: Character torso with open neck and wrist seams for head/hand modularity.
6. `non_manifold_region.json`: T-junction edge shared by 3 faces and a bowtie vertex.
7. `degenerate_faces.json`: Mesh containing 4 zero-area triangular slivers.
8. `mirrored_uv_overlap.json`: Symmetrical character with overlapping left/right UV islands on tile (0, 0).
9. `mesh_with_shape_keys.json`: Head mesh with 12 facial blendshapes (`smile`, `blink_l`, etc.).
10. `weighted_character.json`: Skinned humanoid character with 4 deform weights per vertex.
11. `bad_weights_good_geometry.json`: Physically clean finger geometry where index finger bone pulls middle finger vertices.
12. `good_weights_bad_geometry.json`: Properly mapped bone weights on a hand where finger digits are physically merged.
13. `fingers_touching_not_merged.json`: Distinct finger meshes in resting pose with surface clearance $< 0.5\text{mm}$.
14. `fingers_geometrically_merged.json`: Continuous quads bridging gap between thumb and index finger.
15. `custom_four_finger_character.json`: Stylized creature with exactly 4 digits per hand.
16. `topology_changed_region_stale.json`: Paired before/after states proving region invalidation upon revision increment.

---

## 17. Risk Register

| Risk ID | Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R1** | Auto-retopology yields inconsistent quality across diverse geometry. | HIGH | Classify broad auto-retopology as Phase E research; prioritize Phase B controlled cleanup. |
| **R2** | Topology changes silently destroy UVs, weights, or shape keys. | CRITICAL | Enforce Data Preservation Matrix; block apply unless user confirms transfer strategy. |
| **R3** | Geometric metrics fail to guarantee pleasing deformation. | MEDIUM | Pair static topology checks with non-destructive test posing (`deformation.run_pose_checks`). |
| **R4** | Automated hand/finger detection produces false landmarks. | MEDIUM | When heuristic confidence $< 85\%$, prompt user for interactive landmark confirmation (`NEEDS_INPUT`). |
| **R5** | Weight transfer on complex joints introduces clipping artifacts. | HIGH | Provide isolated preview copy; mandate visual user review before finalizing receipt. |
| **R6** | Geometric algorithms on 200k+ meshes freeze Blender UI. | HIGH | Chunk BMesh operations, yield control, and utilize `bpy.app.timers.register` for async dispatch. |
| **R7** | Blender main-thread threading violations cause crashes. | CRITICAL | Strictly isolate `bpy` access to Blender main thread; background daemon threads handle only I/O. |
| **R8** | Unsaved in-memory Blender state makes durable checkpoints stale. | CRITICAL | Trigger `NEEDS_INPUT` when `bpy.data.is_dirty` before allowing durable mutation checkpoints. |
| **R9** | External retopology libraries impose GPL/commercial licensing conflicts. | HIGH | Document licenses explicitly; prohibit embedding proprietary or GPL-incompatible binaries. |
| **R10** | Godot runtime performance varies across diverse target hardware. | MEDIUM | Base advice on user-selected hardware target (Mobile vs Desktop) and measurable drawcall cost. |

---

## 18. Official API References

1. **Blender BMesh Module**:
   - `bmesh.from_edit_mesh` / `bmesh.new()` / `bm.from_mesh(mesh)`: Primary interface for topology queries.
   - `bmesh.types.BMVert.is_manifold`, `bmesh.types.BMEdge.is_manifold`: Fast programmatic manifold inspection.
   - `bmesh.ops.find_doubles`: Scale-relative duplicate vertex detection.
   - Official Ref: [https://docs.blender.org/api/current/bmesh.html](https://docs.blender.org/api/current/bmesh.html)
2. **Blender Evaluated Depsgraph & Timers**:
   - `bpy.context.evaluated_depsgraph_get()`: Inspecting evaluated geometry with modifiers active.
   - `bpy.app.timers.register`: Safe asynchronous main-thread UI dispatch.
   - Official Ref: [https://docs.blender.org/api/current/bpy.app.timers.html](https://docs.blender.org/api/current/bpy.app.timers.html)
3. **Godot Engine 4.x glTF & Skeleton Import**:
   - `Skeleton3D` and `Skin`: Import transformation and vertex weight binding standards.
   - 4-weight skinning optimization: Standard `StandardMaterial3D` vertex shader performance limit.
   - Retargeting 3D Skeletons: Hand/finger bone orientation standards in Godot 4.
   - Official Ref: [https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)
