"""Deterministic request hashing utilities for RigMate mutation operations.

Pure Python standard library (hashlib, json). Zero external dependencies.
Safe for Blender, Core, and standalone test runtimes.
"""

import hashlib
import json
from typing import Any, Dict, Union


def compute_operation_request_hash(op: Union[Any, Dict[str, Any]]) -> str:
    """
    Compute canonical deterministic SHA-256 hash of operation intent.

    Fields included:
      - project_id
      - host_instance_id
      - document_id
      - tool
      - mode (string value)
      - target_ids (preserves sequence order as documented)
      - expected_revision
      - arguments
      - prepared_plan_ref
      - checkpoint_ref

    Fields excluded:
      - ephemeral values (timestamps, temporary status, transient error states)
      - operation_id (allows matching duplicate intent under different attempt tokens if required,
        while operation identity itself is verified separately in registries).
    """
    if isinstance(op, dict):
        mode_val = op.get("mode")
        if hasattr(mode_val, "value"):
            mode_val = mode_val.value
        canonical_dict = {
            "project_id": op.get("project_id"),
            "host_instance_id": op.get("host_instance_id"),
            "document_id": op.get("document_id"),
            "tool": op.get("tool"),
            "mode": str(mode_val) if mode_val is not None else None,
            "target_ids": list(op.get("target_ids", [])),
            "expected_revision": op.get("expected_revision"),
            "arguments": op.get("arguments", {}),
            "prepared_plan_ref": op.get("prepared_plan_ref"),
            "checkpoint_ref": op.get("checkpoint_ref"),
        }
    else:
        mode_val = getattr(op, "mode", None)
        if hasattr(mode_val, "value"):
            mode_val = mode_val.value
        target_ids = getattr(op, "target_ids", [])
        canonical_dict = {
            "project_id": getattr(op, "project_id", None),
            "host_instance_id": getattr(op, "host_instance_id", None),
            "document_id": getattr(op, "document_id", None),
            "tool": getattr(op, "tool", None),
            "mode": str(mode_val) if mode_val is not None else None,
            "target_ids": list(target_ids) if target_ids else [],
            "expected_revision": getattr(op, "expected_revision", None),
            "arguments": getattr(op, "arguments", {}),
            "prepared_plan_ref": getattr(op, "prepared_plan_ref", None),
            "checkpoint_ref": getattr(op, "checkpoint_ref", None),
        }

    encoded = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
