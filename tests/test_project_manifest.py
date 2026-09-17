"""Unit tests for ProjectManifest core model."""

import json
import pytest
from pydantic import ValidationError
from rigmate.core.project import ProjectManifest, ProjectMode, ProjectRoots


def test_project_manifest_default_and_roundtrip():
    manifest = ProjectManifest(
        project_id="hero_character_hunyuan",
        display_name="Hunyuan 3D Hero Character (Nhân vật Chiến Binh)",
        mode=ProjectMode.MODE_3D,
    )

    assert manifest.project_id == "hero_character_hunyuan"
    assert manifest.database_mode == "none"
    assert manifest.rigmate_account_required is False
    assert manifest.target_platforms == ["godot4"]

    # Serialization and JSON round-trip
    dumped_json = manifest.model_dump_json()
    assert "Nhân vật Chiến Binh" in dumped_json

    restored = ProjectManifest.model_validate_json(dumped_json)
    assert restored.project_id == manifest.project_id
    assert restored.display_name == manifest.display_name
    assert restored.mode == ProjectMode.MODE_3D


def test_project_manifest_rejection_of_cloud_and_database():
    # Rejection of database_mode != 'none'
    with pytest.raises(ValidationError):
        ProjectManifest(
            project_id="test",
            display_name="Test",
            database_mode="sqlite",  # type: ignore
        )

    # Rejection of rigmate_account_required != False
    with pytest.raises(ValidationError):
        ProjectManifest(
            project_id="test",
            display_name="Test",
            rigmate_account_required=True,  # type: ignore
        )


def test_project_manifest_empty_project_id_rejected():
    with pytest.raises(ValidationError):
        ProjectManifest(
            project_id="   ",
            display_name="Test",
        )
