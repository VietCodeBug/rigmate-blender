"""Provider capability definitions and evidence tracking.

A capability is never assumed to be True merely because an executable exists on the machine.
Explicit evidence must be recorded.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CapabilityEvidence(str, Enum):
    OFFICIAL_DOC = "official_doc"          # Stated in official provider vendor documentation
    RUNTIME_PROBE = "runtime_probe"        # Confirmed via runtime API probe/handshake
    PROVIDER_RESPONSE = "provider_response"# Confirmed directly in provider JSON response
    MOCK = "mock"                          # Explicit test mock fixture


class ProviderCapabilities(BaseModel):
    """
    Detailed capability matrix for an AI provider.
    All capability flags default to False until verified by concrete evidence.
    """
    provider_name: str
    text_chat: bool = False
    tool_calls: bool = False
    images: bool = False
    stream: bool = False
    resume_session: bool = False
    cancel: bool = False
    quota_read: bool = False
    usage_report: bool = False
    local_execution: bool = False

    # Evidence audit trail for each capability
    evidence: Dict[str, CapabilityEvidence] = Field(default_factory=dict)
    notes: Optional[str] = None

    def record_evidence(self, capability: str, evidence_type: CapabilityEvidence) -> None:
        """Record evidence for a capability."""
        if not hasattr(self, capability):
            raise ValueError(f"Unknown capability: '{capability}'")
        self.evidence[capability] = evidence_type

    def has_capability(self, capability: str) -> bool:
        """Check if capability is enabled."""
        return bool(getattr(self, capability, False))


def create_mock_capabilities(provider_name: str = "mock") -> ProviderCapabilities:
    """Convenience factory creating verified mock capabilities for testing."""
    caps = ProviderCapabilities(
        provider_name=provider_name,
        text_chat=True,
        tool_calls=True,
        stream=False,
        resume_session=True,
        cancel=True,
        quota_read=True,
        usage_report=True,
        local_execution=True,
    )
    for feat in ["text_chat", "tool_calls", "resume_session", "cancel", "quota_read", "usage_report", "local_execution"]:
        caps.record_evidence(feat, CapabilityEvidence.MOCK)
    return caps
