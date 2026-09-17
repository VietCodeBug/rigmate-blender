"""Extract data safely from bpy to Core Models (supports stub mode when Blender is absent)."""

from rigmate.core.dto import (
    SceneInfo,
    MeshInfo,
    ArmatureInfo,
    BoneInfo,
    TransformData,
    SceneObjectSummary,
    VertexWeightSummary,
)

# Attempt safe bpy import
try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore
    mathutils = None  # type: ignore


class BpyInspector:
    """Read bpy scene graph from Blender Main Thread and map into Core Models."""

    @staticmethod
    def is_blender_environment() -> bool:
        return HAS_BPY

    @classmethod
    def get_scene_info(cls) -> SceneInfo:
        """Read overall active scene state."""
        if not HAS_BPY or bpy is None:
            return SceneInfo(
                active_object_name="Mock_Hunyuan_Character",
                selected_object_names=["Mock_Hunyuan_Character", "Mock_Meshy_Armature"],
                objects=[
                    SceneObjectSummary(name="Mock_Hunyuan_Character", type="MESH", is_selected=True, is_active=True),
                    SceneObjectSummary(name="Mock_Meshy_Armature", type="ARMATURE", is_selected=True, is_active=False),
                ],
                unit_system="METRIC",
            )

        context = bpy.context
        active_obj = context.active_object
        selected_objs = context.selected_objects

        summaries: List[SceneObjectSummary] = []
        for obj in context.scene.objects:
            summaries.append(
                SceneObjectSummary(
                    name=obj.name,
                    type=obj.type,
                    is_selected=(obj in selected_objs),
                    is_active=(obj == active_obj),
                    parent_name=obj.parent.name if obj.parent else None,
                )
            )

        unit_sys = context.scene.unit_settings.system if hasattr(context.scene, "unit_settings") else "METRIC"

        return SceneInfo(
            active_object_name=active_obj.name if active_obj else None,
            selected_object_names=[o.name for o in selected_objs],
            objects=summaries,
            unit_system=unit_sys,
        )

    @classmethod
    def get_selected_context(cls) -> Dict[str, Any]:
        """
        Collect compact context for selected objects (avoids streaming 50k vertex coordinates).
        Gathers summary metadata for active and selected objects only.
        """
        if not HAS_BPY or bpy is None:
            return {
                "active_object": {
                    "name": "Mock_Hunyuan_Character",
                    "type": "MESH",
                    "vertex_count": 52400,
                    "modifiers": ["ARMATURE"],
                    "transform_applied": True,
                },
                "selected_objects": [
                    {"name": "Mock_Hunyuan_Character", "type": "MESH"},
                    {"name": "Mock_Meshy_Armature", "type": "ARMATURE"},
                ],
                "selection_count": 2,
            }

        context = bpy.context
        active_obj = context.active_object
        selected_objs = context.selected_objects

        active_summary = None
        if active_obj:
            mod_names = [m.type for m in getattr(active_obj, "modifiers", [])]
            v_count = len(active_obj.data.vertices) if active_obj.type == "MESH" and hasattr(active_obj, "data") else 0
            is_applied = (
                all(abs(s - 1.0) < 1e-4 for s in active_obj.scale)
                and all(abs(r) < 1e-4 for r in active_obj.rotation_euler)
            )
            active_summary = {
                "name": active_obj.name,
                "type": active_obj.type,
                "vertex_count": v_count,
                "modifiers": mod_names,
                "transform_applied": is_applied,
            }

        selected_summaries = [
            {"name": o.name, "type": o.type}
            for o in selected_objs
        ]

        return {
            "active_object": active_summary,
            "selected_objects": selected_summaries,
            "selection_count": len(selected_objs),
        }

    @classmethod
    def get_mesh_info(cls, obj_name: str) -> Optional[MeshInfo]:
        """Read mesh properties of a specific object."""
        if not HAS_BPY or bpy is None:
            # Standalone mock for Hunyuan 3D character mesh
            return MeshInfo(
                name=obj_name,
                vertex_count=52400,
                edge_count=104800,
                polygon_count=52400,
                has_armature_modifier=True,
                target_armature_name="Meshy_Armature",
                transform=TransformData(
                    location=[0.0, 0.0, 0.0],
                    rotation_euler=[0.0, 0.0, 0.0],
                    scale=[1.0, 1.0, 1.0],
                ),
                vertex_groups=["Hips", "Spine", "Head", "Hand.L", "Hand.R"],
                weights_summary=VertexWeightSummary(
                    unweighted_vertex_count=0,
                    max_weights_per_vertex=4,
                    exceeds_godot_max_weights=False,
                ),
                materials_count=1,
            )

        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != "MESH":
            return None

        mesh_data = obj.data
        has_armature = False
        target_arm_name = None
        for mod in obj.modifiers:
            if mod.type == "ARMATURE":
                has_armature = True
                if mod.object:
                    target_arm_name = mod.object.name
                break

        # Read object transform
        transform = TransformData(
            location=[float(x) for x in obj.location],
            rotation_euler=[float(x) for x in obj.rotation_euler],
            scale=[float(x) for x in obj.scale],
        )

        v_groups = [g.name for g in obj.vertex_groups]

        return MeshInfo(
            name=obj.name,
            vertex_count=len(mesh_data.vertices),
            edge_count=len(mesh_data.edges),
            polygon_count=len(mesh_data.polygons),
            has_armature_modifier=has_armature,
            target_armature_name=target_arm_name,
            transform=transform,
            vertex_groups=v_groups,
            materials_count=len(obj.material_slots),
        )

    @classmethod
    def get_armature_info(cls, obj_name: str) -> Optional[ArmatureInfo]:
        """Read armature hierarchy and bone definitions."""
        if not HAS_BPY or bpy is None:
            # Standalone mock for Meshy armature
            bones = {
                "Hips": BoneInfo(name="Hips", children_names=["Spine", "Thigh.L", "Thigh.R"]),
                "Spine": BoneInfo(name="Spine", parent_name="Hips", children_names=["Chest"]),
                "Chest": BoneInfo(name="Chest", parent_name="Spine", children_names=["Neck", "Arm.L", "Arm.R"]),
                "Arm.L": BoneInfo(name="Arm.L", parent_name="Chest", children_names=["Forearm.L"]),
                "Forearm.L": BoneInfo(name="Forearm.L", parent_name="Arm.L", children_names=["Hand.L"]),
                "Hand.L": BoneInfo(name="Hand.L", parent_name="Forearm.L", children_names=[]),
            }
            return ArmatureInfo(
                name=obj_name,
                bones=bones,
                root_bone_names=["Hips"],
                transform=TransformData(),
                total_bones=len(bones),
                deform_bones_count=len(bones),
            )

        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != "ARMATURE":
            return None

        arm_data = obj.data
        bones_dict: Dict[str, BoneInfo] = {}
        root_bones: List[str] = []

        for b in arm_data.bones:
            parent_name = b.parent.name if b.parent else None
            children = [c.name for c in b.children]
            if not parent_name:
                root_bones.append(b.name)

            bones_dict[b.name] = BoneInfo(
                name=b.name,
                parent_name=parent_name,
                children_names=children,
                head=[float(x) for x in b.head_local],
                tail=[float(x) for x in b.tail_local],
                length=float(b.length),
                connected=b.use_connect,
                use_deform=b.use_deform,
            )

        transform = TransformData(
            location=[float(x) for x in obj.location],
            rotation_euler=[float(x) for x in obj.rotation_euler],
            scale=[float(x) for x in obj.scale],
        )

        return ArmatureInfo(
            name=obj.name,
            bones=bones_dict,
            root_bone_names=root_bones,
            transform=transform,
            total_bones=len(bones_dict),
            deform_bones_count=sum(1 for b in bones_dict.values() if b.use_deform),
        )

