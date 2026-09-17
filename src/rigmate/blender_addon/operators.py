"""Các Operator xử lý tương tác của người dùng trong Blender Add-on."""

try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore

from rigmate.blender_addon.bpy_inspectors import BpyInspector
from rigmate.blender_addon.client import RigMateBridgeClient


if HAS_BPY:
    # Client đơn nhất cho phiên add-on
    bridge_client = RigMateBridgeClient()

    class RIGMATE_OT_check_connection(bpy.types.Operator):
        """Kiểm tra trạng thái kết nối tới RigMate Bridge."""
        bl_idname = "rigmate.check_connection"
        bl_label = "Kiểm tra kết nối"

        def execute(self, context):
            res = bridge_client.check_health()
            props = context.scene.rigmate_props
            if res.get("status") == "online":
                props.is_connected = True
                props.current_provider = res.get("provider", "mock")
                props.active_model = res.get("model", "default")
                self.report({'INFO'}, f"Kết nối thành công tới Bridge ({props.current_provider})")
            else:
                props.is_connected = False
                self.report({'WARNING'}, "Không tìm thấy RigMate Bridge. Hãy chạy 'python -m rigmate.bridge' trước.")
            return {'FINISHED'}

    class RIGMATE_OT_send_chat(bpy.types.Operator):
        """Gửi câu hỏi của người dùng tới RigMate Bridge."""
        bl_idname = "rigmate.send_chat"
        bl_label = "Gửi tin nhắn"

        def execute(self, context):
            props = context.scene.rigmate_props
            text = props.user_input_text.strip()
            if not text:
                return {'CANCELLED'}

            # Thêm tin nhắn user vào danh sách hiển thị
            item = props.chat_messages.add()
            item.sender = "USER"
            item.text = text

            props.is_busy = True
            props.user_input_text = ""

            # Thu thập ngữ cảnh nếu được bật (ngữ cảnh gọn, không gửi 50k vertex)
            context_data = None
            if props.send_selected_only:
                context_data = BpyInspector.get_selected_context()

            def _on_success(response_data):
                def _update_ui():
                    props.is_busy = False
                    
                    # BLOCKER B FIX: Cập nhật active_session_id từ phản hồi của Bridge
                    new_session_id = response_data.get("session_id")
                    if new_session_id:
                        props.active_session_id = new_session_id

                    resp = response_data.get("response", {})
                    resp_text = resp.get("text", "Không nhận được phản hồi.")

                    # Thêm phản hồi AI
                    ai_item = props.chat_messages.add()
                    ai_item.sender = "AI"
                    ai_item.text = resp_text

                    # Cập nhật tokens
                    usage = resp.get("token_usage", {})
                    props.last_tokens_used = usage.get("total_tokens", 0)
                    return None

                bpy.app.timers.register(_update_ui)

            def _on_error(err_msg):
                def _update_err():
                    props.is_busy = False
                    err_item = props.chat_messages.add()
                    err_item.sender = "SYSTEM"
                    err_item.text = f"Lỗi: {err_msg}"
                    return None

                bpy.app.timers.register(_update_err)

            bridge_client.send_chat_async(
                message=text,
                session_id=props.active_session_id or None,
                context_data=context_data,
                on_success=_on_success,
                on_error=_on_error,
            )

            return {'FINISHED'}

    class RIGMATE_OT_cancel_chat(bpy.types.Operator):
        """Hủy yêu cầu AI đang thực thi."""
        bl_idname = "rigmate.cancel_chat"
        bl_label = "Dừng yêu cầu"

        def execute(self, context):
            props = context.scene.rigmate_props
            # BLOCKER B FIX: Thực sự gửi lệnh cancel lên server nếu có session active
            cancelled = False
            if props.active_session_id:
                cancelled = bridge_client.cancel_request(props.active_session_id)
            props.is_busy = False
            if cancelled:
                self.report({'INFO'}, "Đã hủy tác vụ đang xử lý trên Bridge.")
            else:
                self.report({'INFO'}, "Đã gửi tín hiệu dừng tới giao diện.")
            return {'FINISHED'}

    class RIGMATE_OT_new_session(bpy.types.Operator):
        """Bắt đầu một phiên trò chuyện mới."""
        bl_idname = "rigmate.new_chat_session"
        bl_label = "Phiên mới"

        def execute(self, context):
            props = context.scene.rigmate_props
            props.chat_messages.clear()
            # Reset active_session_id để lượt chat tiếp theo tạo phiên mới
            props.active_session_id = ""
            props.last_tokens_used = 0
            self.report({'INFO'}, "Đã tạo phiên hội thoại mới.")
            return {'FINISHED'}

    class RIGMATE_OT_diagnose_scene(bpy.types.Operator):
        """Thực hiện chẩn đoán nhanh Mesh và Armature đang chọn."""
        bl_idname = "rigmate.diagnose_scene"
        bl_label = "Chẩn đoán nhanh Rig"

        def execute(self, context):
            props = context.scene.rigmate_props
            active_obj = context.active_object
            if not active_obj:
                self.report({'WARNING'}, "Chưa chọn object nào trong 3D View.")
                return {'CANCELLED'}

            from rigmate.core.analyzer import RigAnalyzer
            mesh_info = None
            armature_info = None

            if active_obj.type == "MESH":
                mesh_info = BpyInspector.get_mesh_info(active_obj.name)
                # Tìm armature liên kết nếu có
                if mesh_info and mesh_info.target_armature_name:
                    armature_info = BpyInspector.get_armature_info(mesh_info.target_armature_name)
            elif active_obj.type == "ARMATURE":
                armature_info = BpyInspector.get_armature_info(active_obj.name)

            report = RigAnalyzer.analyze(mesh=mesh_info, armature=armature_info)

            # Thêm báo cáo vào panel chat
            item = props.chat_messages.add()
            item.sender = "DIAGNOSTIC"
            item.text = f"{report.summary_text}\n" + "\n".join(
                [f"• [{i.severity}] {i.title}: {i.message}" for i in report.issues]
            )

            self.report({'INFO'}, f"Hoàn thành chẩn đoán ({len(report.issues)} ghi chú).")
            return {'FINISHED'}

    class RIGMATE_OT_manual_quota_dialog(bpy.types.Operator):
        """Hộp thoại nhập snapshot hạn mức AI thủ công (từ /usage)."""
        bl_idname = "rigmate.manual_quota_dialog"
        bl_label = "Nhập hạn mức thủ công"

        remaining: bpy.props.FloatProperty(name="Hạn mức còn lại", default=100.0)  # type: ignore
        total: bpy.props.FloatProperty(name="Tổng hạn mức", default=100.0)  # type: ignore
        unit: bpy.props.StringProperty(name="Đơn vị", default="credits")  # type: ignore

        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)

        def execute(self, context):
            props = context.scene.rigmate_props
            
            # BLOCKER D FIX: Gửi persist snapshot qua Bridge client lên StorageManager
            provider_name = props.current_provider or "Unknown"
            model_name = props.active_model or "Unknown"
            quota_tot = self.total if self.total > 0 else None

            res = bridge_client.update_manual_quota(
                provider_name=provider_name,
                model_name=model_name,
                quota_remaining=self.remaining,
                quota_total=quota_tot,
                quota_unit=self.unit,
            )

            if res.get("status") == "saved":
                props.is_manual_quota = True
                props.has_quota_percentage = (quota_tot is not None and quota_tot > 0)
                if props.has_quota_percentage:
                    props.energy_percentage = (self.remaining / self.total) * 100.0
                    props.quota_display_label = f"{(self.remaining / self.total) * 100.0:.1f}% ({self.remaining:g}/{self.total:g} {self.unit}) [Nhập thủ công]"
                else:
                    props.energy_percentage = 0.0
                    props.quota_display_label = f"{self.remaining:g} {self.unit} [Nhập thủ công]"
                self.report({'INFO'}, "Đã lưu snapshot hạn mức thủ công vào Storage.")
            else:
                err = res.get("message", "Không thể kết nối Bridge.")
                self.report({'ERROR'}, f"Lỗi lưu hạn mức: {err}")
else:
    RIGMATE_OT_check_connection = None  # type: ignore
    RIGMATE_OT_send_chat = None  # type: ignore
    RIGMATE_OT_cancel_chat = None  # type: ignore
    RIGMATE_OT_new_session = None  # type: ignore
    RIGMATE_OT_diagnose_scene = None  # type: ignore
    RIGMATE_OT_manual_quota_dialog = None  # type: ignore
