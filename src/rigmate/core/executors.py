"""Operation execution protocol and deterministic fake test executor.

Defines:
- OperationExecutor: Protocol for host execution (Blender/Godot/Fake)
- FakeOperationExecutor: In-memory/filesystem test fake supporting simulated faults:
  - Stale revision rejection
  - ACK loss simulation (mutation executed, receipt recorded in host, exception raised to caller)
  - Postcondition failures
  - Non-cancellable operations
  - Query status recovery
"""

from typing import Dict, List, Optional, Protocol, runtime_checkable
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.receipts import OperationReceipt, ReceiptError, ReceiptStatus
from rigmate.core.time_utils import to_utc_iso


@runtime_checkable
class OperationExecutor(Protocol):
    """Host execution interface."""

    def prepare(self, operation: OperationEnvelope) -> bool:
        """Validate preconditions on the host."""
        ...

    def apply(self, operation: OperationEnvelope) -> OperationReceipt:
        """Apply mutation on the host."""
        ...

    def verify(self, operation: OperationEnvelope, receipt: OperationReceipt) -> bool:
        """Verify postconditions on the host."""
        ...

    def query_status(self, operation_id: str, idempotency_key: str) -> Optional[OperationReceipt]:
        """Query host for durable status of an operation (used after ACK loss)."""
        ...


class FakeOperationExecutor:
    """
    Deterministic test executor implementing OperationExecutor.
    Tracks mutation calls, host revisions, and simulates ACK loss and stale revision faults.
    """

    def __init__(
        self,
        current_revision: str = "rev_1",
        next_revision: str = "rev_2",
        simulate_ack_loss: bool = False,
        simulate_stale_revision: bool = False,
        simulate_verify_failure: bool = False,
    ):
        self.current_revision = current_revision
        self.next_revision = next_revision
        self.simulate_ack_loss = simulate_ack_loss
        self.simulate_stale_revision = simulate_stale_revision
        self.simulate_verify_failure = simulate_verify_failure

        self.mutation_count: int = 0
        self.executed_operations: Dict[str, OperationReceipt] = {}
        self.idempotency_records: Dict[str, str] = {}  # key -> operation_id

    def prepare(self, operation: OperationEnvelope) -> bool:
        if self.simulate_stale_revision or operation.expected_revision != self.current_revision:
            raise RigMateError(
                f"Host revision '{self.current_revision}' does not match expected '{operation.expected_revision}'",
                code=RigMateErrorCode.TARGET_STALE,
                details={
                    "current_revision": self.current_revision,
                    "expected_revision": operation.expected_revision,
                },
            )
        return True

    def apply(self, operation: OperationEnvelope) -> OperationReceipt:
        # Precondition check
        if self.simulate_stale_revision or operation.expected_revision != self.current_revision:
            raise RigMateError(
                f"Host revision '{self.current_revision}' does not match expected '{operation.expected_revision}'",
                code=RigMateErrorCode.TARGET_STALE,
                details={
                    "current_revision": self.current_revision,
                    "expected_revision": operation.expected_revision,
                },
            )

        # Increment real mutation counter
        self.mutation_count += 1
        rev_before = self.current_revision
        self.current_revision = self.next_revision

        receipt = OperationReceipt(
            operation_id=operation.operation_id,
            status=ReceiptStatus.COMPLETED,
            host_revision_before=rev_before,
            host_revision_after=self.current_revision,
            facts={"mutated_targets": operation.target_ids, "count": self.mutation_count},
            changes=[{"target": t, "action": "fake_applied"} for t in operation.target_ids],
            verified_at=to_utc_iso(),
        )

        # Host persists durable record of execution
        self.executed_operations[operation.operation_id] = receipt
        self.idempotency_records[operation.idempotency_key] = operation.operation_id

        # Simulate ACK-loss: host successfully mutated and saved receipt, but network/ACK dropped!
        if self.simulate_ack_loss:
            self.simulate_ack_loss = False  # Trigger only once
            raise ConnectionResetError("Simulated network ACK loss: host mutated but response was dropped")

        return receipt

    def verify(self, operation: OperationEnvelope, receipt: OperationReceipt) -> bool:
        if self.simulate_verify_failure:
            return False
        return receipt.host_revision_after == self.current_revision

    def query_status(self, operation_id: str, idempotency_key: str) -> Optional[OperationReceipt]:
        if operation_id in self.executed_operations:
            return self.executed_operations[operation_id]
        if idempotency_key in self.idempotency_records:
            op_id = self.idempotency_records[idempotency_key]
            return self.executed_operations.get(op_id)
        return None
