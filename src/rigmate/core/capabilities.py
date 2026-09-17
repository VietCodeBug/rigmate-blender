"""Generic capability registry for host platforms, engines, and providers.

A capability is never assumed to be True merely because an executable exists on the machine.
Explicit declaration and evidence are required.
"""

from typing import Dict, Optional, Set
from pydantic import BaseModel, Field


class CapabilityEntry(BaseModel):
    name: str
    enabled: bool = True
    evidence: Optional[str] = None
    notes: Optional[str] = None


class CapabilityRegistry(BaseModel):
    """
    Registry tracking available system, host, engine, or provider capabilities.
    """
    entries: Dict[str, CapabilityEntry] = Field(default_factory=dict)

    def register(self, name: str, enabled: bool = True, evidence: Optional[str] = None, notes: Optional[str] = None) -> None:
        """Register or update a capability entry."""
        self.entries[name] = CapabilityEntry(
            name=name,
            enabled=enabled,
            evidence=evidence,
            notes=notes,
        )

    def has(self, name: str) -> bool:
        """Check if capability is registered and enabled. Defaults to False for unknown."""
        entry = self.entries.get(name)
        return bool(entry and entry.enabled)

    def require(self, name: str) -> None:
        """Enforce that capability is present and enabled; raises KeyError if missing/disabled."""
        if not self.has(name):
            raise KeyError(f"Required capability '{name}' is not available in registry")

    def merge(self, other: "CapabilityRegistry") -> None:
        """Merge another capability registry into this one (overwriting with newest entry)."""
        for name, entry in other.entries.items():
            self.entries[name] = entry.model_copy()

    def get_enabled_names(self) -> Set[str]:
        """Return set of all enabled capability names."""
        return {name for name, entry in self.entries.items() if entry.enabled}
