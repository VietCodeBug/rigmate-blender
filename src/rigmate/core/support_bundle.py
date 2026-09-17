"""Support bundle manifest metadata model.

Defines the structure and safety constraints of diagnostic support bundles.
Strictly excludes authentication tokens, passwords, and provider keys.
"""

import platform
import sys
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso


class SupportBundleManifest(BaseModel):
    """
    Manifest describing the contents, environmental context, and redaction level
    of an exported diagnostic support bundle.
    """
    schema_version: str = "1.0.0"
    created_at: str = Field(default_factory=to_utc_iso)
    rigmate_version: str = "0.1.0"
    os_name: str = Field(default_factory=platform.system)
    os_version: str = Field(default_factory=platform.version)
    python_version: str = Field(default_factory=lambda: sys.version.split()[0])
    project_id: Optional[str] = None
    included_categories: List[str] = Field(default_factory=lambda: ["diagnostics", "logs", "metadata"])
    redaction_applied: bool = True
    evidence_levels: Dict[str, str] = Field(default_factory=dict)
    known_limitations: List[str] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def validate_utc(cls, v: str) -> str:
        parse_utc_iso(v)
        return v
