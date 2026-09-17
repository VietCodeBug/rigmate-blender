"""Unit tests for SupportBundleManifest model."""

import pytest
from pydantic import ValidationError
from rigmate.core.support_bundle import SupportBundleManifest


def test_support_bundle_manifest_default_and_roundtrip():
    manifest = SupportBundleManifest(
        project_id="proj_hero",
        evidence_levels={"blender": "mock", "antigravity": "unverified"},
        known_limitations=["Blender runtime not verified on this worker"],
    )

    assert manifest.schema_version == "1.0.0"
    assert manifest.created_at.endswith("Z")
    assert manifest.redaction_applied is True
    assert manifest.evidence_levels["antigravity"] == "unverified"

    # Serialization test
    dumped = manifest.model_dump_json()
    assert "proj_hero" in dumped
    loaded = SupportBundleManifest.model_validate_json(dumped)
    assert loaded.project_id == "proj_hero"


def test_support_bundle_manifest_invalid_timestamp():
    with pytest.raises(ValidationError):
        SupportBundleManifest(created_at="not_a_valid_timestamp")
