"""Unit tests for provider capabilities model and evidence audit trail."""

import pytest
from pydantic import ValidationError
from rigmate.providers.capabilities import (
    ProviderCapabilities,
    CapabilityEvidence,
    create_mock_capabilities,
)


def test_provider_capabilities_explicit_defaults():
    # Capabilities must default to False until verified by concrete evidence
    caps = ProviderCapabilities(provider_name="unverified_provider")
    assert caps.text_chat is False
    assert caps.tool_calls is False
    assert caps.local_execution is False
    assert len(caps.evidence) == 0


def test_provider_capabilities_mock_factory():
    caps = create_mock_capabilities("mock")
    assert caps.text_chat is True
    assert caps.has_capability("tool_calls") is True
    assert caps.has_capability("images") is False
    assert caps.evidence["text_chat"] == CapabilityEvidence.MOCK


def test_provider_capabilities_evidence_recording():
    caps = ProviderCapabilities(provider_name="custom_ai")
    caps.text_chat = True
    caps.record_evidence("text_chat", CapabilityEvidence.RUNTIME_PROBE)

    assert caps.evidence["text_chat"] == CapabilityEvidence.RUNTIME_PROBE

    with pytest.raises(ValueError, match="Unknown capability"):
        caps.record_evidence("non_existent_cap", CapabilityEvidence.OFFICIAL_DOC)


def test_provider_capabilities_invalid_evidence_type():
    with pytest.raises(ValidationError):
        ProviderCapabilities.model_validate({
            "provider_name": "test",
            "evidence": {"text_chat": "unsupported_evidence_string"},
        })

