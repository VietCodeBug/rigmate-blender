"""Unit tests for generic capability registry."""

import pytest
from rigmate.core.capabilities import CapabilityRegistry


def test_capability_registry_has_and_require():
    reg = CapabilityRegistry()
    reg.register("blender.read", enabled=True, evidence="addon_connected")
    reg.register("blender.write", enabled=False, notes="disabled_in_v0.1")

    assert reg.has("blender.read") is True
    assert reg.has("blender.write") is False
    assert reg.has("blender.unknown_tool") is False

    reg.require("blender.read")
    with pytest.raises(KeyError):
        reg.require("blender.write")


def test_capability_registry_merge():
    reg1 = CapabilityRegistry()
    reg1.register("godot.editor", enabled=True)

    reg2 = CapabilityRegistry()
    reg2.register("provider.tool_calls", enabled=True)
    reg2.register("godot.editor", enabled=False, notes="overridden")

    reg1.merge(reg2)

    assert reg1.has("provider.tool_calls") is True
    assert reg1.has("godot.editor") is False
    assert reg1.entries["godot.editor"].notes == "overridden"
