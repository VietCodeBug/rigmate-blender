"""Tests for neutral host protocol contracts, JSON serializability, and read-only invariants."""

import json
import pytest

from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.host_protocol import (
    DocumentIdentity,
    HostAdapter,
    HostApplyResult,
    HostIdentity,
    HostOperationExecutionState,
    HostOperationStatus,
    HostType,
    HostVerificationResult,
    InspectionRequest,
    InspectionResult,
    PreparedHostOperation,
)
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.testing.durable_host import DurableFakeHost


def test_host_protocol_json_roundtrip():
    """All host protocol models must serialize to JSON and deserialize cleanly with no leaky types."""
    # 1. HostIdentity
    host_id = HostIdentity(host_instance_id="host_test", host_type=HostType.FAKE.value, protocol_version="1.0.0")
    dumped = host_id.model_dump()
    json_str = json.dumps(dumped)
    loaded = HostIdentity(**json.loads(json_str))
    assert loaded.host_instance_id == "host_test"

    # 2. DocumentIdentity
    doc_id = DocumentIdentity(project_id="proj_1", document_id="doc_1", revision="rev_1")
    dumped = doc_id.model_dump()
    json_str = json.dumps(dumped)
    loaded = DocumentIdentity(**json.loads(json_str))
    assert loaded.revision == "rev_1"

    # 3. InspectionRequest & Result
    req = InspectionRequest(project_id="proj_1", document_id="doc_1", include_weights=True)
    res = InspectionResult(document=doc_id, facts={"vertices": 50000}, scene_objects=[{"name": "Mesh"}])
    res_dump = res.model_dump()
    loaded_res = InspectionResult(**json.loads(json.dumps(res_dump)))
    assert loaded_res.facts["vertices"] == 50000

    # 4. PreparedHostOperation
    prep = PreparedHostOperation(
        operation_id="op_1",
        document=doc_id,
        tool="object.rename",
        mode=OperationMode.APPLY.value,
        can_apply=True,
    )
    loaded_prep = PreparedHostOperation(**json.loads(json.dumps(prep.model_dump())))
    assert loaded_prep.can_apply is True

    # 5. HostApplyResult
    apply_res = HostApplyResult(
        operation_id="op_1",
        execution_state=HostOperationExecutionState.APPLIED.value,
        host_revision_before="rev_1",
        host_revision_after="rev_2",
        facts={"count": 1},
        changes=[{"target": "Character", "action": "renamed"}],
    )
    loaded_apply = HostApplyResult(**json.loads(json.dumps(apply_res.model_dump())))
    assert loaded_apply.host_revision_after == "rev_2"

    # 6. HostVerificationResult
    ver_res = HostVerificationResult(
        operation_id="op_1",
        verified=True,
        verified_revision="rev_2",
        evidence={"mutation_count": 1},
    )
    loaded_ver = HostVerificationResult(**json.loads(json.dumps(ver_res.model_dump())))
    assert loaded_ver.verified is True


def test_inspect_is_strictly_read_only(tmp_path):
    """inspect_document must never change revision or increment mutation_count."""
    host = DurableFakeHost(tmp_path / "host_state", initial_revision="rev_1")
    assert host.mutation_count == 0

    req = InspectionRequest(project_id="proj_1", document_id="doc_1")
    res = host.inspect_document(req)

    assert res.document.revision == "rev_1"
    assert host.mutation_count == 0


def test_prepare_is_strictly_read_only(tmp_path):
    """prepare_operation must validate preconditions without mutating state."""
    host = DurableFakeHost(tmp_path / "host_state", initial_revision="rev_1")
    assert host.mutation_count == 0

    op = OperationEnvelope(
        operation_id="op_prep_test",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_prep_test",
        arguments={"new_name": "Character_New"},

    )

    prepared = host.prepare_operation(op)
    assert prepared.can_apply is True
    assert host.mutation_count == 0

    # Document revision on disk must still be rev_1
    doc = host.get_or_create_document("doc_1")
    assert doc["current_revision"] == "rev_1"
    assert doc["mutation_count"] == 0


def test_headless_no_bpy_import():
    """Verify that Core host protocol and DurableFakeHost run headlessly without bpy."""
    import sys
    # Explicitly ensure bpy is not present
    assert "bpy" not in sys.modules

    from rigmate.core.host_protocol import HostAdapter, HostApplyResult
    from rigmate.testing.durable_host import DurableFakeHost

    assert issubclass(DurableFakeHost, HostAdapter)
