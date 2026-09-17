"""Unit tests for OperationEnvelope domain model."""

import pytest
from pydantic import ValidationError
from rigmate.core.operations import OperationEnvelope, OperationMode


def test_operation_envelope_valid_inspect_and_preview():
    op = OperationEnvelope(
        operation_id="op_100",
        job_id="job_200",
        project_id="proj_300",
        host_instance_id="host_blender_01",
        document_id="doc_character",
        tool="mesh.inspect_density",
        mode=OperationMode.INSPECT,
        idempotency_key="key_001",
        target_ids=["mesh_hero", "armature_hero"],
        arguments={"threshold": 50000},
    )

    assert op.mode == OperationMode.INSPECT
    assert len(op.target_ids) == 2


def test_operation_envelope_target_ids_duplicates_rejected():
    with pytest.raises(ValidationError, match="target_ids must not contain duplicate identifiers"):
        OperationEnvelope(
            operation_id="op_100",
            job_id="job_200",
            project_id="proj_300",
            host_instance_id="host_blender_01",
            document_id="doc_character",
            tool="mesh.inspect",
            mode=OperationMode.INSPECT,
            idempotency_key="key_001",
            target_ids=["mesh_hero", "mesh_hero"],  # Duplicate!
        )


def test_operation_envelope_apply_mode_requires_plan_and_checkpoint():
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
            idempotency_key="key_001",
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
            idempotency_key="key_001",
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
        idempotency_key="key_001",
        checkpoint_ref=None,  # Allowed for checkpoint.create!
        prepared_plan_ref="plan_001",
    )
    assert op_cp_create.tool == "checkpoint.create"
