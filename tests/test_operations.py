"""Unit tests for OperationEnvelope domain model."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from rigmate.core.operations import OperationEnvelope, OperationMode


def test_operation_envelope_valid_inspect_preview_and_apply():
    # 1. Valid inspect
    op_inspect = OperationEnvelope(
        operation_id="op_100",
        job_id="job_200",
        project_id="proj_300",
        host_instance_id="host_blender_01",
        document_id="doc_character",
        tool="mesh.inspect_density",
        mode=OperationMode.INSPECT,
        expected_revision="rev_1",
        idempotency_key="key_001",
        target_ids=["mesh_hero", "armature_hero"],
        arguments={"threshold": 50000},
    )
    assert op_inspect.mode == OperationMode.INSPECT
    assert len(op_inspect.target_ids) == 2
    assert op_inspect.expected_revision == "rev_1"

    # 2. Valid preview
    op_preview = OperationEnvelope(
        operation_id="op_101",
        job_id="job_200",
        project_id="proj_300",
        host_instance_id="host_blender_01",
        document_id="doc_character",
        tool="mesh.preview_decimate",
        mode=OperationMode.PREVIEW,
        expected_revision="rev_1",
        idempotency_key="key_002",
        target_ids=["mesh_hero"],
    )
    assert op_preview.mode == OperationMode.PREVIEW

    # 3. Valid apply
    op_apply = OperationEnvelope(
        operation_id="op_102",
        job_id="job_200",
        project_id="proj_300",
        host_instance_id="host_blender_01",
        document_id="doc_character",
        tool="mesh.apply_decimate",
        mode=OperationMode.APPLY,
        expected_revision="rev_1",
        idempotency_key="key_003",
        target_ids=["mesh_hero"],
        checkpoint_ref="cp_001",
        prepared_plan_ref="plan_001",
    )
    assert op_apply.mode == OperationMode.APPLY


def test_operation_envelope_target_ids_rules():
    # Must contain at least one target ID
    with pytest.raises(ValidationError, match="target_ids must contain at least one target identifier"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=[],  # Empty!
        )

    # Must reject duplicates
    with pytest.raises(ValidationError, match="target_ids must not contain duplicate identifiers"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero", "mesh_hero"],  # Duplicate!
        )


def test_operation_envelope_expected_revision_rules():
    # Reject missing / None expected_revision
    with pytest.raises(ValidationError):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision=None,  # type: ignore
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
        )

    # Reject blank / empty expected_revision
    with pytest.raises(ValidationError, match="expected_revision.*must be a non-empty string"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="   ",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
        )


def test_operation_envelope_schema_version_and_required_ids():
    # Unsupported schema version
    with pytest.raises(ValidationError):
        OperationEnvelope(
            schema_version="2.0.0",  # type: ignore
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
        )

    # Empty required ID
    with pytest.raises(ValidationError, match="operation_id.*must be a non-empty string"):
        OperationEnvelope(
            operation_id="",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
        )


def test_operation_envelope_arguments_json_compatibility():
    # Non-JSON-compatible arguments (e.g. raw Path object or NaN)
    with pytest.raises(ValidationError, match="arguments validation failed"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
            arguments={"invalid_path": Path("/not/json")},
        )

    with pytest.raises(ValidationError, match="arguments validation failed"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
            arguments={"nan_val": float("nan")},
        )


def test_operation_envelope_apply_mode_plan_and_checkpoint_rules():
    # 1. Missing prepared_plan_ref in apply mode
    with pytest.raises(ValidationError, match="require a valid prepared_plan_ref"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.decimate",
            mode=OperationMode.APPLY,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
            checkpoint_ref="cp_999",
            prepared_plan_ref=None,
        )

    # 2. Missing checkpoint_ref in apply mode
    with pytest.raises(ValidationError, match="requires a valid checkpoint_ref"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.decimate",
            mode=OperationMode.APPLY,
            expected_revision="rev_1",
            idempotency_key="key_001",
            target_ids=["mesh_hero"],
            checkpoint_ref=None,
            prepared_plan_ref="plan_123",
        )

    # 3. Special exception: tool == 'checkpoint.create' is allowed without existing checkpoint_ref
    op_cp_create = OperationEnvelope(
        operation_id="op_100",
        job_id="job_200",
        project_id="proj_300",
        host_instance_id="host_blender_01",
        document_id="doc_character",
        tool="checkpoint.create",
        mode=OperationMode.APPLY,
        expected_revision="rev_1",
        idempotency_key="key_001",
        target_ids=["mesh_hero"],
        checkpoint_ref=None,  # Allowed for checkpoint.create!
        prepared_plan_ref="plan_001",
    )
    assert op_cp_create.tool == "checkpoint.create"
