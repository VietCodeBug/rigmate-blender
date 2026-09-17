"""Giao diện Blender Add-on: Sidebar panel, Thanh năng lượng và Trò chuyện."""

try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore


if HAS_BPY:
    class VIEW3D_PT_rigmate_main(bpy.types.Panel):
        """Panel chính của RigMate trên Sidebar 3D View."""
        bl_label = "RigMate - AI Rig Assistant"
        bl_idname = "VIEW3D_PT_rigmate_main"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "RigMate"

        def draw(self, context):
            layout = self.layout
            scene = context.scene
            rm_props = getattr(scene, "rigmate_props", None)

            if not rm_props:
                layout.label(text="Đang tải dữ liệu RigMate...", icon="INFO")
                return

            # 1. Trạng thái kết nối (Connection Status)
            box_conn = layout.box()
            row_conn = box_conn.row(align=True)
            if rm_props.is_connected:
                row_conn.label(text=f"Đã kết nối ({rm_props.current_provider})", icon="CHECKMARK")
            else:
                row_conn.label(text="Chưa kết nối Bridge", icon="CANCEL")
            row_conn.operator("rigmate.check_connection", text="Kiểm tra", icon="FILE_REFRESH")

            # 2. Thanh năng lượng & Hạn mức AI (Energy Bar & AI Quota)
            box_quota = layout.box()
            box_quota.label(text="Hạn mức & Năng lượng AI", icon="SOLO_ON")

            # Hiển thị thông tin Provider & Model
            row_prov = box_quota.row()
            row_prov.label(text=f"Mô hình: {rm_props.active_model}")

            # Hiển thị Thanh năng lượng nếu có phần trăm
            if rm_props.has_quota_percentage:
                col_energy = box_quota.column(align=True)
                col_energy.prop(rm_props, "energy_percentage", text="Năng lượng", slider=True)
                col_energy.label(text=rm_props.quota_display_label)
            else:
                box_quota.label(text=rm_props.quota_display_label, icon="INFO")

            # Nút nhập thủ công nếu không đọc tự động được
            if rm_props.is_manual_quota or not rm_props.has_quota_percentage:
                box_quota.operator("rigmate.manual_quota_dialog", text="Cập nhật Quota thủ công", icon="GREASEPENCIL")

            # Phân biệt token lượt này với quota tổng
            if rm_props.last_tokens_used > 0:
                box_quota.label(text=f"Token lượt gần nhất: {rm_props.last_tokens_used:,}", icon="RECOVER_LAST")

            # Ngày hết hạn gói (trường riêng biệt)
            if rm_props.plan_expiration_text:
                box_quota.label(text=f"Hạn gói: {rm_props.plan_expiration_text}", icon="TIME")

            # 3. Khu vực Tùy chọn Ngữ cảnh (Context Options)
            box_ctx = layout.box()
            box_ctx.prop(rm_props, "send_selected_only", text="Chỉ gửi thông tin Object được chọn")
            box_ctx.operator("rigmate.diagnose_scene", text="Chẩn đoán nhanh Scene/Rig", icon="DIAGNOSTIC")

            # 4. Lịch sử trò chuyện (Chat History)
            box_chat = layout.box()
            box_chat.label(text="Lịch sử hội thoại", icon="COMMUNITY")

            # Hiển thị các tin nhắn gần nhất
            col_msgs = box_chat.column(align=True)
            if not rm_props.chat_messages:
                col_msgs.label(text="Chưa có tin nhắn nào. Hãy đặt câu hỏi!")
            else:
                for msg in rm_props.chat_messages[-4:]:
                    r = col_msgs.row()
                    icon = "USER" if msg.sender == "USER" else "SHADERFX"
                    r.label(text=f"[{msg.sender}]: {msg.text[:40]}...", icon=icon)

            # 5. Ô nhập và Nút gửi / Hủy
            box_input = layout.box()
            box_input.prop(rm_props, "user_input_text", text="")
            row_actions = box_input.row(align=True)

            if rm_props.is_busy:
                row_actions.operator("rigmate.cancel_chat", text="Dừng lại", icon="CANCEL")
            else:
                row_actions.operator("rigmate.send_chat", text="Gửi", icon="PLAY")

            row_actions.operator("rigmate.new_chat_session", text="Mới", icon="ADD")
else:
    # Lớp rỗng khi chạy trong môi trường không có bpy
    VIEW3D_PT_rigmate_main = None  # type: ignore
