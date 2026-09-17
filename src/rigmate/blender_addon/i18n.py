"""Localization and internationalization (i18n) layer for RigMate Blender Addon.

Canonical source language: English ('en').
Supported locales: English ('en'), Vietnamese ('vi').
Completely decoupled from Pydantic and external server libraries.
"""

from typing import Dict, Any, Optional

DEFAULT_LOCALE = "en"

# Translations dictionary structured by locale code
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # General & Status
        "app.name": "RigMate - AI Rig Assistant",
        "status.connected": "Connected ({provider})",
        "status.disconnected": "Disconnected from Bridge",
        "status.checking": "Checking connection...",
        "btn.check": "Check Connection",
        "btn.send": "Send",
        "btn.stop": "Stop",
        "btn.new_chat": "New",
        "btn.diagnose": "Quick Diagnose Scene/Rig",
        "btn.update_quota": "Update Quota Manually",
        "prompt.empty_chat": "No messages yet. Ask a question or diagnose your rig!",
        "prompt.enter_message": "Ask RigMate...",

        # Quota & Energy Level
        "quota.title": "AI Energy & Quota",
        "quota.model_label": "Model: {model}",
        "quota.energy_label": "Energy Level",
        "quota.auto_unavailable": "Automatic quota data is unavailable",
        "quota.unknown": "Unknown Quota",
        "quota.exhausted": "Quota Exhausted (0 remaining)",
        "quota.unsupported": "Quota checking unsupported by provider",
        "quota.tag_manual": "[Manual Entry]",
        "quota.tag_demo": "[DEMO]",
        "quota.tag_stale": "(Stale Data)",
        "quota.last_tokens": "Last Turn Tokens: {tokens}",
        "quota.plan_expiration": "Plan Expiration: {expiration}",
        "quota.saved_success": "Manual quota snapshot saved to Storage.",
        "quota.saved_error": "Failed to save quota: {error}",

        # Dialogs
        "dialog.manual_quota_title": "Enter Quota Snapshot Manually",
        "dialog.remaining": "Remaining Quota",
        "dialog.total": "Total Quota",
        "dialog.unit": "Unit",

        # Chat
        "chat.history_title": "Chat History",
        "chat.no_response": "No response received.",
        "chat.error_prefix": "Error: {error}",

        # Context
        "context.send_selected_only": "Send selected object info only",
        "context.no_active_object": "No active object selected in 3D View.",
        "context.diag_completed": "Diagnosis complete ({count} findings).",

        # Session & Operators
        "session.new_created": "Created new chat session.",
        "session.cancelled": "Task stopped.",
        "session.bridge_cancelled": "Task cancelled on Bridge.",
        "session.bridge_not_found": "RigMate Bridge not found. Run 'python -m rigmate.bridge' first.",
        "session.bridge_connected": "Connected to Bridge ({provider}).",

        # Locale
        "locale.label": "Language",

        # Error codes
        "error.bridge.error": "Bridge error encountered.",
        "error.bridge.connection_failed": "Unable to connect to the RigMate Bridge. Please verify it is running.",
        "error.bridge.auth_failed": "Authentication with RigMate Bridge failed. Check runtime token.",
        "error.bridge.timeout": "Request to RigMate Bridge timed out.",
        "error.bridge.http_error": "Bridge returned an HTTP error.",

        # Diagnostics
        "diag.high_poly_title": "High vertex count ({count:,} vertices)",
        "diag.high_poly_msg": (
            "Hunyuan 3D meshes typically have dense vertex topology (~50k vertices). "
            "While fully riggable in Blender, this vertex count may reduce real-time performance in Godot. "
            "Recommendation: Consider using Decimate or Remesh modifier before final shape key/anim export."
        ),
        "diag.high_poly_action": "Use Decimate or Remesh modifier if targeting real-time Godot gameplay.",
        "diag.poly_ok_title": "Vertex count suitable ({count:,} vertices)",
        "diag.poly_ok_msg": "Vertex count is within safe limits for display and animation.",
        "diag.mesh_unapplied_transform_title": "Mesh transforms not applied",
        "diag.mesh_unapplied_transform_msg": (
            "Mesh '{name}' has unapplied Scale or non-zero Rotation. "
            "This may cause distortion during skinning or engine export."
        ),
        "diag.mesh_unapplied_transform_action": "Apply all transforms (Ctrl+A in Blender) before binding bones.",
        "diag.no_armature_mod_title": "Mesh has no Armature Modifier",
        "diag.no_armature_mod_msg": "Mesh '{name}' is not bound to any armature modifier.",
        "diag.no_armature_mod_action": "Add an Armature Modifier and select target armature.",
        "diag.armature_unapplied_transform_title": "Armature transforms not applied",
        "diag.armature_unapplied_transform_msg": (
            "Armature '{name}' has unapplied Scale or Rotation. "
            "When exporting to Godot, bones might be rotated or scaled unexpectedly."
        ),
        "diag.armature_unapplied_transform_action": "Apply Armature Transform (Ctrl+A) in Object Mode.",
        "diag.armature_empty_title": "Armature contains no bones",
        "diag.armature_empty_msg": "Armature '{name}' is empty.",
        "diag.finger_not_detected_title": "Finger bones not detected by standard naming",
        "diag.finger_not_detected_msg": (
            "Standard finger bone names (thumb, index, finger_...) were not detected. "
            "This is common if Meshy generated a mitten hand rig or if Hunyuan 3D created fused hands. "
            "Bone names are heuristic suggestions and do not strictly confirm missing fingers."
        ),
        "diag.finger_not_detected_action": "If finger articulation is needed, use RigMate finger tools to generate bone chains.",
        "diag.finger_partial_title": "Finger structure ({side}): Detected {count}/5 finger types by name",
        "diag.finger_partial_msg": (
            "Detected: {detected}. Unmatched: {missing}. "
            "Note: Bone names are heuristic suggestions, not definitive evidence of missing fingers."
        ),
        "diag.finger_complete_title": "Finger structure ({side}): Matched all 5 finger groups",
        "diag.finger_complete_msg": "All 5 standard finger bone chains detected ({side}).",
        "diag.summary": "Diagnostic analysis complete for Mesh: [{mesh}] and Armature: [{armature}]. Total findings: {count} (Warnings: {warnings}, Errors: {errors}). Godot export readiness: {score}.",
        "diag.score_good": "GOOD",
        "diag.score_caution": "NEEDS ATTENTION",
        "diag.score_fix": "NEEDS FIX",
        "side.left": "Left Hand",
        "side.right": "Right Hand",
        "side.hand": "Hand",
    },
    "vi": {
        # General & Status
        "app.name": "RigMate - Trợ lý Rig AI",
        "status.connected": "Đã kết nối ({provider})",
        "status.disconnected": "Chưa kết nối Bridge",
        "status.checking": "Đang kiểm tra kết nối...",
        "btn.check": "Kiểm tra kết nối",
        "btn.send": "Gửi",
        "btn.stop": "Dừng lại",
        "btn.new_chat": "Mới",
        "btn.diagnose": "Chẩn đoán nhanh Scene/Rig",
        "btn.update_quota": "Cập nhật Quota thủ công",
        "prompt.empty_chat": "Chưa có tin nhắn nào. Hãy đặt câu hỏi hoặc chẩn đoán rig!",
        "prompt.enter_message": "Hỏi RigMate...",

        # Quota & Energy Level
        "quota.title": "Hạn mức & Năng lượng AI",
        "quota.model_label": "Mô hình: {model}",
        "quota.energy_label": "Mức năng lượng",
        "quota.auto_unavailable": "Chưa đọc được hạn mức tự động",
        "quota.unknown": "Không rõ hạn mức",
        "quota.exhausted": "Đã hết hạn mức (còn 0)",
        "quota.unsupported": "Nhà cung cấp không hỗ trợ kiểm tra hạn mức",
        "quota.tag_manual": "[Nhập thủ công]",
        "quota.tag_demo": "[DEMO]",
        "quota.tag_stale": "(Dữ liệu cũ)",
        "quota.last_tokens": "Token lượt gần nhất: {tokens}",
        "quota.plan_expiration": "Hạn gói: {expiration}",
        "quota.saved_success": "Đã lưu snapshot hạn mức thủ công vào Storage.",
        "quota.saved_error": "Lỗi lưu hạn mức: {error}",

        # Dialogs
        "dialog.manual_quota_title": "Nhập hạn mức thủ công",
        "dialog.remaining": "Hạn mức còn lại",
        "dialog.total": "Tổng hạn mức",
        "dialog.unit": "Đơn vị",

        # Chat
        "chat.history_title": "Lịch sử hội thoại",
        "chat.no_response": "Không nhận được phản hồi.",
        "chat.error_prefix": "Lỗi: {error}",

        # Context
        "context.send_selected_only": "Chỉ gửi thông tin Object được chọn",
        "context.no_active_object": "Chưa chọn object nào trong 3D View.",
        "context.diag_completed": "Hoàn thành chẩn đoán ({count} ghi chú).",

        # Session & Operators
        "session.new_created": "Đã tạo phiên hội thoại mới.",
        "session.cancelled": "Đã hủy tác vụ.",
        "session.bridge_cancelled": "Đã hủy tác vụ đang xử lý trên Bridge.",
        "session.bridge_not_found": "Không tìm thấy RigMate Bridge. Hãy chạy 'python -m rigmate.bridge' trước.",
        "session.bridge_connected": "Kết nối thành công tới Bridge ({provider}).",

        # Locale
        "locale.label": "Ngôn ngữ",

        # Error codes
        "error.bridge.error": "Gặp lỗi Bridge.",
        "error.bridge.connection_failed": "Không thể kết nối Bridge RigMate. Vui lòng kiểm tra xem Bridge đã chạy chưa.",
        "error.bridge.auth_failed": "Xác thực với Bridge thất bại. Hãy kiểm tra token runtime.",
        "error.bridge.timeout": "Yêu cầu tới Bridge RigMate bị quá thời gian (timeout).",
        "error.bridge.http_error": "Bridge trả về lỗi HTTP.",

        # Diagnostics
        "diag.high_poly_title": "Số lượng đỉnh cao ({count:,} đỉnh)",
        "diag.high_poly_msg": (
            "Mô hình Hunyuan 3D gốc thường có mật độ đỉnh dày (~50k đỉnh). "
            "Mặc dù rig được trong Blender, số lượng đỉnh này có thể gây giảm hiệu năng khi xuất sang Godot. "
            "Khuyến nghị: cân nhắc Decimate hoặc Remesh trước khi tạo shape key/anim hoàn chỉnh."
        ),
        "diag.high_poly_action": "Dùng modifier Decimate hoặc Remesh nếu hướng tới game thời gian thực trong Godot.",
        "diag.poly_ok_title": "Số lượng đỉnh phù hợp ({count:,} đỉnh)",
        "diag.poly_ok_msg": "Số lượng đỉnh mesh ở mức an toàn cho hiển thị và hoạt họa.",
        "diag.mesh_unapplied_transform_title": "Transform của Mesh chưa được áp dụng (Apply)",
        "diag.mesh_unapplied_transform_msg": (
            "Mesh '{name}' có Scale hoặc Rotation khác chuẩn chưa apply. "
            "Điều này dễ gây méo mesh khi gắn xương hoặc xuất sang engine."
        ),
        "diag.mesh_unapplied_transform_action": "Thực hiện 'Apply All Transforms' (Ctrl+A trong Blender) trước khi bind xương.",
        "diag.no_armature_mod_title": "Mesh chưa có Armature Modifier",
        "diag.no_armature_mod_msg": "Mesh '{name}' chưa được liên kết với bộ xương nào qua Modifier.",
        "diag.no_armature_mod_action": "Thêm Armature Modifier và chỉ định target armature.",
        "diag.armature_unapplied_transform_title": "Transform của Armature chưa được áp dụng (Apply)",
        "diag.armature_unapplied_transform_msg": (
            "Bộ xương '{name}' có Scale hoặc Rotation chưa áp dụng. "
            "Khi xuất FBX/glTF sang Godot, xương có thể bị xoay lệch hoặc sai kích thước."
        ),
        "diag.armature_unapplied_transform_action": "Apply Transform cho Armature (Ctrl+A) ở Object Mode.",
        "diag.armature_empty_title": "Armature không có bone nào",
        "diag.armature_empty_msg": "Bộ xương '{name}' rỗng.",
        "diag.finger_not_detected_title": "Chưa phát hiện xương ngón tay theo quy ước tên phổ biến",
        "diag.finger_not_detected_msg": (
            "Không tìm thấy tên xương ngón tay thông thường (thumb, index, finger_...). "
            "Đây là trường hợp bình thường nếu mô hình Meshy tạo rig đơn giản dạng bàn tay nắm (mitten hand) "
            "hoặc mô hình Hunyuan 3D có bàn tay dính liền. "
            "Tên xương chỉ là gợi ý heuristic, không khẳng định mô hình bị thiếu ngón."
        ),
        "diag.finger_not_detected_action": "Nếu nhân vật cần cử động ngón, có thể dùng công cụ RigMate để thêm chuỗi xương ngón.",
        "diag.finger_partial_title": "Gợi ý cấu trúc ngón ({side}): Phát hiện {count}/5 loại ngón theo tên",
        "diag.finger_partial_msg": (
            "Nhận diện được: {detected}. Chưa khớp từ khóa cho: {missing}. "
            "Lưu ý: Tên xương chỉ mang tính gợi ý, không khẳng định mô hình bị thiếu ngón nếu rig dùng quy ước riêng."
        ),
        "diag.finger_complete_title": "Cấu trúc ngón ({side}): Khớp đủ 5 nhóm ngón theo tên chuẩn",
        "diag.finger_complete_msg": "Đã phát hiện đầy đủ các chuỗi xương cho 5 ngón ({side}).",
        "diag.summary": "Đã hoàn thành phân tích chẩn đoán cho Mesh: [{mesh}] và Armature: [{armature}]. Tổng số phát hiện: {count} (Cảnh báo: {warnings}, Lỗi: {errors}). Đánh giá sơ bộ xuất Godot: {score}.",
        "diag.score_good": "TỐT",
        "diag.score_caution": "CẦN LƯU Ý",
        "diag.score_fix": "CẦN SỬA",
        "side.left": "Tay trái",
        "side.right": "Tay phải",
        "side.hand": "Bàn tay",
    }
}

# Current active locale (default English)
_current_locale = DEFAULT_LOCALE


def set_locale(locale: str):
    """Set the active locale. Falls back to DEFAULT_LOCALE if unsupported."""
    global _current_locale
    if locale in TRANSLATIONS:
        _current_locale = locale
    else:
        _current_locale = DEFAULT_LOCALE


def get_locale() -> str:
    """Return the currently active locale identifier."""
    return _current_locale


def get_available_locales() -> list[str]:
    """Return a list of all registered locale identifiers."""
    return list(TRANSLATIONS.keys())


def register_locale(locale: str, strings: Dict[str, str]):
    """Register or extend a locale translation table."""
    if locale not in TRANSLATIONS:
        TRANSLATIONS[locale] = {}
    TRANSLATIONS[locale].update(strings)


def t(key: str, locale: Optional[str] = None, **kwargs: Any) -> str:
    """Translate a key into localized string with fallback to default locale."""
    target_locale = locale or _current_locale
    val = TRANSLATIONS.get(target_locale, {}).get(key)
    
    if val is None and target_locale != DEFAULT_LOCALE:
        val = TRANSLATIONS.get(DEFAULT_LOCALE, {}).get(key)

    if val is None:
        val = key

    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
