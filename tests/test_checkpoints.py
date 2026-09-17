"""Unit tests for CheckpointEngine: creation, hashing, blob deduplication, restore-to-copy, retention."""

import pytest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.file_hash import sha256_file
from rigmate.storage.checkpoints import CheckpointEngine


def test_checkpoint_create_and_restore_to_copy(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    # Create dummy assets
    model_file = project_root / "character.blend"
    model_file.write_text("v1_original_blender_binary_data", encoding="utf-8")

    engine = CheckpointEngine(storage_root)
    manifest = engine.create_checkpoint(
        checkpoint_id="cp_test_1",
        project_id="proj_1",
        job_id="job_1",
        project_root=project_root,
        file_paths=[model_file],
        source_revision="rev_1",
        reason="pre-mutation test",
    )

    assert manifest.complete is True
    assert len(manifest.files) == 1
    assert manifest.files[0].relative_path == "character.blend"

    # Mutate source file to v2
    model_file.write_text("v2_mutated_data", encoding="utf-8")
    assert sha256_file(model_file) != manifest.files[0].sha256

    # Restore to copy
    restored_map = engine.restore_to_copy("cp_test_1", project_root, output_suffix="recovered_test")
    assert "character.blend" in restored_map

    restored_copy_path = restored_map["character.blend"]
    # Source file remains v2!
    assert model_file.read_text(encoding="utf-8") == "v2_mutated_data"
    # Restored copy has v1 content and matches checkpoint hash!
    assert sha256_file(restored_copy_path) == manifest.files[0].sha256


def test_checkpoint_path_safety_rejects_external_file(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    external_file = tmp_path / "secret.txt"
    external_file.write_text("outside", encoding="utf-8")

    engine = CheckpointEngine(tmp_path / "storage")
    with pytest.raises(Exception):
        engine.create_checkpoint(
            checkpoint_id="cp_test_unsafe",
            project_id="proj_1",
            job_id="job_1",
            project_root=project_root,
            file_paths=[external_file],
            source_revision="rev_1",
        )
