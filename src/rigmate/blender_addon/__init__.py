"""RigMate Blender Add-on: Register properties, operators, and UI panels."""

bl_info = {
    "name": "RigMate - AI Rig Assistant",
    "author": "RigMate Contributors",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > RigMate Tab",
    "description": "AI-powered rig inspection and refinement assistant (Hunyuan 3D, Meshy) targeting Godot export.",
    "category": "Rigging",
    "license": "GPL-3.0-or-later",
}

try:
    import bpy  # type: ignore
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    bpy = None  # type: ignore

if HAS_BPY:
    from .ui import VIEW3D_PT_rigmate_main
    from .operators import (
        RIGMATE_OT_check_connection,
        RIGMATE_OT_send_chat,
        RIGMATE_OT_cancel_chat,
        RIGMATE_OT_new_session,
        RIGMATE_OT_diagnose_scene,
        RIGMATE_OT_manual_quota_dialog,
    )

    from .i18n import set_locale, get_locale

    def _on_locale_change(self, context):
        set_locale(self.ui_locale)

    class RigMateChatMessageItem(bpy.types.PropertyGroup):
        sender: bpy.props.StringProperty(name="Sender", default="")  # type: ignore
        text: bpy.props.StringProperty(name="Text", default="")  # type: ignore

    class RigMateSceneProperties(bpy.types.PropertyGroup):
        ui_locale: bpy.props.EnumProperty(
            name="Language",
            description="UI display language",
            items=[
                ("en", "English", "English (Default)"),
                ("vi", "Tiếng Việt", "Vietnamese"),
            ],
            default="en",
            update=_on_locale_change,
        )  # type: ignore
        is_connected: bpy.props.BoolProperty(name="Connected", default=False)  # type: ignore
        current_provider: bpy.props.StringProperty(name="Provider", default="mock")  # type: ignore
        active_model: bpy.props.StringProperty(name="Model", default="mock-hunyuan-assistant")  # type: ignore
        active_session_id: bpy.props.StringProperty(name="Session ID", default="")  # type: ignore

        # Quota & Energy Level
        has_quota_percentage: bpy.props.BoolProperty(name="Has Percentage", default=False)  # type: ignore
        energy_percentage: bpy.props.FloatProperty(name="Energy %", default=0.0, min=0.0, max=100.0)  # type: ignore
        quota_display_label: bpy.props.StringProperty(name="Quota Label", default="Automatic quota data is unavailable")  # type: ignore
        is_manual_quota: bpy.props.BoolProperty(name="Manual Quota", default=False)  # type: ignore
        last_tokens_used: bpy.props.IntProperty(name="Last Tokens", default=0)  # type: ignore
        plan_expiration_text: bpy.props.StringProperty(name="Plan Expiration", default="")  # type: ignore

        # Context & Input
        send_selected_only: bpy.props.BoolProperty(name="Send Selected Only", default=True)  # type: ignore
        user_input_text: bpy.props.StringProperty(name="User Input", default="")  # type: ignore
        is_busy: bpy.props.BoolProperty(name="Busy", default=False)  # type: ignore

        # Chat message collection
        chat_messages: bpy.props.CollectionProperty(type=RigMateChatMessageItem)  # type: ignore


    classes = (
        RigMateChatMessageItem,
        RigMateSceneProperties,
        VIEW3D_PT_rigmate_main,
        RIGMATE_OT_check_connection,
        RIGMATE_OT_send_chat,
        RIGMATE_OT_cancel_chat,
        RIGMATE_OT_new_session,
        RIGMATE_OT_diagnose_scene,
        RIGMATE_OT_manual_quota_dialog,
    )


    def register():
        for cls in classes:
            bpy.utils.register_class(cls)
        bpy.types.Scene.rigmate_props = bpy.props.PointerProperty(type=RigMateSceneProperties)


    def unregister():
        del bpy.types.Scene.rigmate_props
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
else:
    def register():
        pass

    def unregister():
        pass


if __name__ == "__main__":
    register()
