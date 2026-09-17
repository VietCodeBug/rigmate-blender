import asyncio
import sys
from pathlib import Path

# Đảm bảo console Windows in được tiếng Việt UTF-8 không lỗi cp950/cp437
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo import được module rigmate từ thư mục src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rigmate.core.analyzer import RigAnalyzer
from rigmate.core.models import (
    MeshInfo,
    ArmatureInfo,
    BoneInfo,
    TransformData,
    VertexWeightSummary,
)
from rigmate.core.quota import QuotaSnapshot, TokenUsage
from rigmate.providers.mock_provider import MockAIProvider
from rigmate.bridge.session import SessionManager
from rigmate.storage.manager import StorageManager


def create_demo_character_data():
    """Tạo dữ liệu mô phỏng nhân vật Hunyuan 3D (52,400 đỉnh) gắn xương qua Meshy."""
    mesh = MeshInfo(
        name="Hunyuan3D_Creature_Mesh",
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
        vertex_groups=["Hips", "Spine", "Chest", "Hand.L", "Hand.R"],
        weights_summary=VertexWeightSummary(
            unweighted_vertex_count=0,
            max_weights_per_vertex=4,
            exceeds_godot_max_weights=False,
        ),
        materials_count=1,
    )

    bones = {
        "Hips": BoneInfo(name="Hips", children_names=["Spine", "Thigh.L", "Thigh.R"]),
        "Spine": BoneInfo(name="Spine", parent_name="Hips", children_names=["Chest"]),
        "Chest": BoneInfo(name="Chest", parent_name="Spine", children_names=["Neck", "Arm.L", "Arm.R"]),
        "Arm.L": BoneInfo(name="Arm.L", parent_name="Chest", children_names=["Forearm.L"]),
        "Forearm.L": BoneInfo(name="Forearm.L", parent_name="Arm.L", children_names=["Hand.L"]),
        "Hand.L": BoneInfo(name="Hand.L", parent_name="Forearm.L", children_names=[]),
        # Giả lập bên phải có ngón cái thumb
        "Arm.R": BoneInfo(name="Arm.R", parent_name="Chest", children_names=["Forearm.R"]),
        "Forearm.R": BoneInfo(name="Forearm.R", parent_name="Arm.R", children_names=["Hand.R"]),
        "Hand.R": BoneInfo(name="Hand.R", parent_name="Forearm.R", children_names=["thumb_01.r"]),
        "thumb_01.r": BoneInfo(name="thumb_01.r", parent_name="Hand.R", children_names=[]),
    }

    # Armature có transform chưa apply để test chẩn đoán
    armature = ArmatureInfo(
        name="Meshy_Armature",
        bones=bones,
        root_bone_names=["Hips"],
        transform=TransformData(
            location=[0.0, 0.0, 0.0],
            rotation_euler=[0.0, 0.0, 0.0],
            scale=[1.02, 1.02, 1.02],  # Chưa apply scale!
        ),
        total_bones=len(bones),
        deform_bones_count=len(bones),
    )

    return mesh, armature


async def main():
    print("=" * 65)
    print("  RIGMATE v0.1 - DEMO CHẨN ĐOÁN & TRÒ CHUYỆN KHÔNG CẦN BLENDER")
    print("=" * 65)

    # 1. Chạy phân tích Rig độc lập
    print("\n[BƯỚC 1] Phân tích mô hình Hunyuan 3D + Xương Meshy:")
    mesh, armature = create_demo_character_data()
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)

    print(f"-> {report.summary_text}")
    print("\nChi tiết các phát hiện:")
    for issue in report.issues:
        print(f"  [{issue.severity}] {issue.title}")
        print(f"    Chi tiết: {issue.message}")
        if issue.suggested_action:
            print(f"    Gợi ý xử lý: {issue.suggested_action}")

    # 2. Thanh năng lượng & Hạn mức AI
    print("\n" + "-" * 65)
    print("[BƯỚC 2] Kiểm tra Thanh Năng Lượng & Quota Snapshot:")
    provider = MockAIProvider()
    quota_snap = await provider.fetch_quota_snapshot()
    print(f"Provider: {quota_snap.provider_name} ({quota_snap.model_name})")
    print(f"Nguồn dữ liệu: {quota_snap.source}")
    print(f"Thanh năng lượng UI: {quota_snap.format_energy_label()}")
    print(f"Chu kỳ reset: {quota_snap.reset_at}")
    print(f"Hạn gói: {quota_snap.plan_expiration}")

    # 3. Trò chuyện thử nghiệm qua Session Manager
    print("\n" + "-" * 65)
    print("[BƯỚC 3] Tương tác Chat giả lập với Session Manager:")
    storage = StorageManager()
    session_mgr = SessionManager(storage)
    session = session_mgr.create_session(provider)

    prompts = [
        "Xin chào RigMate, hãy kiểm tra rig của nhân vật này cho tôi.",
        "Tại sao rig Meshy này không cử động được ngón tay?",
        "Tôi muốn xuất nhân vật này sang Godot, có cần lưu ý gì không?",
    ]

    for p in prompts:
        print(f"\nUser: {p}")
        resp = await session_mgr.send_message(
            session_id=session.session_id,
            user_message=p,
            provider=provider,
            context_data={"mesh_name": mesh.name},
        )
        print(f"RigMate: {resp.text}")
        if resp.token_usage:
            print(f"  (Token tiêu thụ: {resp.token_usage.total_tokens} | Tổng session: {session.total_tokens_used})")

    print("\n" + "=" * 65)
    print("  DEMO HOÀN THÀNH THÀNH CÔNG (100% Core Logic & Session hoạt động!)")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
