"""Timeline formatting and structured debug trace API.

Builds chronologically ordered, human-readable timeline from durable event journal.
"""

from typing import List, Optional
from pydantic import BaseModel
from rigmate.core.events import RigMateEvent
from rigmate.storage.job_store import JobStore


class TimelineEntry(BaseModel):
    sequence: int
    timestamp: str
    event_type: str
    summary: str


def build_job_timeline(job_id: str, store: JobStore) -> List[TimelineEntry]:
    """
    Construct ordered timeline entries from a job's event journal.
    """
    events = store.read_events(job_id)
    timeline: List[TimelineEntry] = []

    for ev in events:
        # Build concise summary
        payload_parts = []
        if "from_status" in ev.payload and "to_status" in ev.payload:
            payload_parts.append(f"{ev.payload['from_status']} -> {ev.payload['to_status']}")
        if "operation_id" in ev.payload:
            payload_parts.append(f"op={ev.payload['operation_id']}")
        if "checkpoint_id" in ev.payload:
            payload_parts.append(f"cp={ev.payload['checkpoint_id']}")
        if "error_code" in ev.payload:
            payload_parts.append(f"err={ev.payload['error_code']}")

        summary = f"[{ev.event_type}]"
        if payload_parts:
            summary += f" ({', '.join(payload_parts)})"

        timeline.append(
            TimelineEntry(
                sequence=ev.sequence,
                timestamp=ev.timestamp,
                event_type=ev.event_type,
                summary=summary,
            )
        )

    return timeline


def format_timeline_text(timeline: List[TimelineEntry]) -> str:
    """Format timeline as human-readable aligned text block."""
    lines = []
    for entry in timeline:
        lines.append(f"{entry.sequence:03d} {entry.timestamp} {entry.summary}")
    return "\n".join(lines)
