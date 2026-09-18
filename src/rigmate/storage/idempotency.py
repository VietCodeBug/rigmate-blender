"""Durable idempotency registry for mutation operations.

Layout:
  <storage_root>/idempotency/<idempotency_key>.json

Features:
- Deterministic canonical request hashing (excluding ephemeral fields)
- Detection of exact replay (returns existing receipt/status)
- Detection of conflict (same idempotency_key + different operation payload -> IDEMPOTENCY_CONFLICT)
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.operations import OperationEnvelope
from rigmate.core.receipts import OperationReceipt
from rigmate.core.time_utils import to_utc_iso
from rigmate.storage.json_io import read_json, write_json_atomic


class IdempotencyRecord(BaseModel):
    idempotency_key: str
    operation_id: str
    request_hash: str
    created_at: str = Field(default_factory=to_utc_iso)
    receipt: Optional[Dict[str, Any]] = None


from rigmate.contracts.hashing import compute_operation_request_hash



class IdempotencyRegistry:
    """
    Durable filesystem-backed registry for operation idempotency keys.
    """

    def __init__(self, storage_root: Union[str, Path]):
        self.storage_root = Path(storage_root).resolve()
        self.reg_dir = self.storage_root / "idempotency"

    def _key_path(self, idempotency_key: str) -> Path:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        return self.reg_dir / f"{key_hash}.json"


    def check(self, op: OperationEnvelope) -> Optional[IdempotencyRecord]:
        """
        Check if idempotency key was previously processed.
        Returns existing record if exact duplicate (same key & request hash).
        Raises RigMateError(IDEMPOTENCY_CONFLICT) if key was used with different request hash.
        Returns None if key is unseen.
        """
        p = self._key_path(op.idempotency_key)
        if not p.is_file():
            return None

        data = read_json(p)
        rec = IdempotencyRecord(**data)
        current_hash = compute_operation_request_hash(op)

        if rec.request_hash != current_hash:
            raise RigMateError(
                f"Idempotency key '{op.idempotency_key}' conflict: request intent does not match previous operation '{rec.operation_id}'",
                code=RigMateErrorCode.IDEMPOTENCY_CONFLICT,
                details={
                    "idempotency_key": op.idempotency_key,
                    "existing_operation_id": rec.operation_id,
                    "existing_hash": rec.request_hash,
                    "new_hash": current_hash,
                },
            )

        return rec

    def register(
        self,
        op: OperationEnvelope,
        receipt: Optional[OperationReceipt] = None,
    ) -> IdempotencyRecord:
        """Persist or update idempotency record."""
        self.reg_dir.mkdir(parents=True, exist_ok=True)
        key_file = self._key_path(op.idempotency_key)
        current_hash = compute_operation_request_hash(op)

        if key_file.is_file():
            existing = IdempotencyRecord(**read_json(key_file))
            if existing.request_hash != current_hash:
                raise RigMateError(
                    f"Cannot register idempotency key '{op.idempotency_key}': request intent differs from existing registration",
                    code=RigMateErrorCode.IDEMPOTENCY_CONFLICT,
                    details={"existing_op": existing.operation_id, "new_op": op.operation_id},
                )
            if existing.operation_id != op.operation_id:
                raise RigMateError(
                    f"Cannot register idempotency key '{op.idempotency_key}': operation_id '{op.operation_id}' does not match existing '{existing.operation_id}'",
                    code=RigMateErrorCode.IDEMPOTENCY_CONFLICT,
                    details={"existing_op": existing.operation_id, "new_op": op.operation_id},
                )
            # Updating receipt for existing record
            if receipt:
                existing.receipt = receipt.model_dump()
                write_json_atomic(key_file, existing.model_dump())
            return existing

        rec = IdempotencyRecord(
            idempotency_key=op.idempotency_key,
            operation_id=op.operation_id,
            request_hash=current_hash,
            receipt=receipt.model_dump() if receipt else None,
        )
        write_json_atomic(key_file, rec.model_dump())
        return rec

