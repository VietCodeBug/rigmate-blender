"""Blender Add-on UI: Sidebar panel, energy bar, and chat interface."""

try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore

from rigmate.core.i18n import t


if HAS_BPY:
    class VIEW3D_PT_rigmate_main(bpy.types.Panel):
        """Main RigMate Sidebar panel in 3D View."""
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
                layout.label(text=t("status.checking"), icon="INFO")
                return

            # 1. Connection Status
            box_conn = layout.box()
            row_conn = box_conn.row(align=True)
            if rm_props.is_connected:
                conn_text = t("status.connected", provider=rm_props.current_provider)
                row_conn.label(text=conn_text, icon="CHECKMARK")
            else:
                row_conn.label(text=t("status.disconnected"), icon="CANCEL")
            row_conn.operator("rigmate.check_connection", text=t("btn.check"), icon="FILE_REFRESH")

            # 2. AI Energy Bar & Quota
            box_quota = layout.box()
            box_quota.label(text=t("quota.title"), icon="SOLO_ON")

            # Provider & Model info
            row_prov = box_quota.row()
            row_prov.label(text=t("quota.model_label", model=rm_props.active_model))

            # Energy bar if percentage available
            if rm_props.has_quota_percentage:
                col_energy = box_quota.column(align=True)
                col_energy.prop(rm_props, "energy_percentage", text=t("quota.energy_label"), slider=True)
                col_energy.label(text=rm_props.quota_display_label)
            else:
                box_quota.label(text=rm_props.quota_display_label, icon="INFO")

            # Manual entry button if automatic read is unavailable or manual snapshot
            if rm_props.is_manual_quota or not rm_props.has_quota_percentage:
                box_quota.operator("rigmate.manual_quota_dialog", text=t("btn.update_quota"), icon="GREASEPENCIL")

            # Last turn token usage
            if rm_props.last_tokens_used > 0:
                box_quota.label(
                    text=t("quota.last_tokens", tokens=f"{rm_props.last_tokens_used:,}"),
                    icon="RECOVER_LAST",
                )

            # Plan expiration date
            if rm_props.plan_expiration_text:
                box_quota.label(
                    text=t("quota.plan_expiration", expiration=rm_props.plan_expiration_text),
                    icon="TIME",
                )

            # 3. Context Options
            box_ctx = layout.box()
            box_ctx.prop(rm_props, "send_selected_only", text=t("context.send_selected_only"))
            box_ctx.operator("rigmate.diagnose_scene", text=t("btn.diagnose"), icon="DIAGNOSTIC")

            # 4. Chat History
            box_chat = layout.box()
            box_chat.label(text=t("chat.history_title"), icon="COMMUNITY")

            # Recent messages
            col_msgs = box_chat.column(align=True)
            if not rm_props.chat_messages:
                col_msgs.label(text=t("prompt.empty_chat"))
            else:
                for msg in rm_props.chat_messages[-4:]:
                    r = col_msgs.row()
                    icon = "USER" if msg.sender == "USER" else "SHADERFX"
                    r.label(text=f"[{msg.sender}]: {msg.text[:40]}...", icon=icon)

            # 5. Input & Action Buttons
            box_input = layout.box()
            box_input.prop(rm_props, "user_input_text", text="")
            row_actions = box_input.row(align=True)

            if rm_props.is_busy:
                row_actions.operator("rigmate.cancel_chat", text=t("btn.stop"), icon="CANCEL")
            else:
                row_actions.operator("rigmate.send_chat", text=t("btn.send"), icon="PLAY")

            row_actions.operator("rigmate.new_chat_session", text=t("btn.new_chat"), icon="ADD")
else:
    VIEW3D_PT_rigmate_main = None  # type: ignore

