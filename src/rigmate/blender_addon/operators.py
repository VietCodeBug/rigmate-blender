"""Operators handling user interaction in the Blender Add-on."""

try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore

from .bpy_inspectors import BpyInspector
from .client import RigMateBridgeClient
from rigmate.core.i18n import t


if HAS_BPY:
    # Singleton client for add-on session
    bridge_client = RigMateBridgeClient()

    class RIGMATE_OT_check_connection(bpy.types.Operator):
        """Check connection status to the RigMate Bridge."""
        bl_idname = "rigmate.check_connection"
        bl_label = "Check Connection"

        def execute(self, context):
            res = bridge_client.check_health()
            props = context.scene.rigmate_props
            if res.get("status") == "online":
                props.is_connected = True
                props.current_provider = res.get("provider", "mock")
                props.active_model = res.get("model", "default")
                self.report({'INFO'}, t("session.bridge_connected", provider=props.current_provider))
            else:
                props.is_connected = False
                self.report({'WARNING'}, t("session.bridge_not_found"))
            return {'FINISHED'}

    class RIGMATE_OT_send_chat(bpy.types.Operator):
        """Send user message to RigMate Bridge."""
        bl_idname = "rigmate.send_chat"
        bl_label = "Send Message"

        def execute(self, context):
            props = context.scene.rigmate_props
            text = props.user_input_text.strip()
            if not text:
                return {'CANCELLED'}

            # Append user message
            item = props.chat_messages.add()
            item.sender = "USER"
            item.text = text

            props.is_busy = True
            props.user_input_text = ""

            # Compact context collection (avoids pushing 50k vertex dumps)
            context_data = None
            if props.send_selected_only:
                context_data = BpyInspector.get_selected_context()

            def _on_success(response_data):
                def _update_ui():
                    props.is_busy = False
                    
                    # Update active_session_id from Bridge response
                    new_session_id = response_data.get("session_id")
                    if new_session_id:
                        props.active_session_id = new_session_id

                    resp = response_data.get("response", {})
                    resp_text = resp.get("text", t("chat.no_response"))

                    # Append AI response
                    ai_item = props.chat_messages.add()
                    ai_item.sender = "AI"
                    ai_item.text = resp_text

                    # Update token statistics
                    usage = resp.get("token_usage", {})
                    props.last_tokens_used = usage.get("total_tokens", 0)
                    return None

                bpy.app.timers.register(_update_ui)

            def _on_error(err_code: str, err_msg: str):
                def _update_err():
                    props.is_busy = False
                    err_item = props.chat_messages.add()
                    err_item.sender = "SYSTEM"
                    localized_err = t(f"error.{err_code}")
                    if localized_err == f"error.{err_code}":
                        # Fallback to internal error message if specific error code key is not translated
                        localized_err = err_msg
                    err_item.text = t("chat.error_prefix", error=localized_err)
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
        """Cancel ongoing AI request."""
        bl_idname = "rigmate.cancel_chat"
        bl_label = "Cancel Request"

        def execute(self, context):
            props = context.scene.rigmate_props
            cancelled = False
            if props.active_session_id:
                cancelled = bridge_client.cancel_request(props.active_session_id)
            props.is_busy = False
            if cancelled:
                self.report({'INFO'}, t("session.bridge_cancelled"))
            else:
                self.report({'INFO'}, t("session.cancelled"))
            return {'FINISHED'}

    class RIGMATE_OT_new_session(bpy.types.Operator):
        """Start a new chat session."""
        bl_idname = "rigmate.new_chat_session"
        bl_label = "New Session"

        def execute(self, context):
            props = context.scene.rigmate_props
            props.chat_messages.clear()
            props.active_session_id = ""
            props.last_tokens_used = 0
            self.report({'INFO'}, t("session.new_created"))
            return {'FINISHED'}

    class RIGMATE_OT_diagnose_scene(bpy.types.Operator):
        """Run quick diagnostic on selected Mesh and Armature."""
        bl_idname = "rigmate.diagnose_scene"
        bl_label = "Diagnose Scene"

        def execute(self, context):
            props = context.scene.rigmate_props
            active_obj = context.active_object
            if not active_obj:
                self.report({'WARNING'}, t("context.no_active_object"))
                return {'CANCELLED'}

            from rigmate.core.analyzer import RigAnalyzer
            mesh_info = None
            armature_info = None

            if active_obj.type == "MESH":
                mesh_info = BpyInspector.get_mesh_info(active_obj.name)
                if mesh_info and mesh_info.target_armature_name:
                    armature_info = BpyInspector.get_armature_info(mesh_info.target_armature_name)
            elif active_obj.type == "ARMATURE":
                armature_info = BpyInspector.get_armature_info(active_obj.name)

            report = RigAnalyzer.analyze(mesh=mesh_info, armature=armature_info)

            # Display diagnostic findings in chat panel
            item = props.chat_messages.add()
            item.sender = "DIAGNOSTIC"
            item.text = f"{report.summary_text}\n" + "\n".join(
                [f"• [{i.severity}] {i.title}: {i.message}" for i in report.issues]
            )

            self.report({'INFO'}, t("context.diag_completed", count=len(report.issues)))
            return {'FINISHED'}

    class RIGMATE_OT_manual_quota_dialog(bpy.types.Operator):
        """Dialog to record a manual AI quota snapshot."""
        bl_idname = "rigmate.manual_quota_dialog"
        bl_label = "Manual Quota Entry"

        remaining: bpy.props.FloatProperty(name="Remaining", default=100.0)  # type: ignore
        total: bpy.props.FloatProperty(name="Total", default=100.0)  # type: ignore
        unit: bpy.props.StringProperty(name="Unit", default="credits")  # type: ignore

        def invoke(self, context, event):
            return context.window_manager.invoke_props_dialog(self)

        def execute(self, context):
            props = context.scene.rigmate_props
            
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
                tag = t("quota.tag_manual")
                if props.has_quota_percentage:
                    props.energy_percentage = (self.remaining / self.total) * 100.0
                    props.quota_display_label = f"{(self.remaining / self.total) * 100.0:.1f}% ({self.remaining:g}/{self.total:g} {self.unit}) {tag}"
                else:
                    props.energy_percentage = 0.0
                    props.quota_display_label = f"{self.remaining:g} {self.unit} {tag}"
                self.report({'INFO'}, t("quota.saved_success"))
            else:
                err = res.get("message", "Bridge connection failed")
                self.report({'ERROR'}, t("quota.saved_error", error=err))
            return {'FINISHED'}
else:
    RIGMATE_OT_check_connection = None  # type: ignore
    RIGMATE_OT_send_chat = None  # type: ignore
    RIGMATE_OT_cancel_chat = None  # type: ignore
    RIGMATE_OT_new_session = None  # type: ignore
    RIGMATE_OT_diagnose_scene = None  # type: ignore
    RIGMATE_OT_manual_quota_dialog = None  # type: ignore
