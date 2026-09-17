"""Core Project Manifest model.

Represents baseline project identity without external database or cloud account requirements.
Pure Python + Pydantic validation (zero bpy dependency).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ProjectMode(str, Enum):
    MODE_2D = "2d"
    MODE_3D = "3d"
    MODE_MIXED = "mixed"


class ProjectRoots(BaseModel):
    """Configured directory roots for project assets and engine files."""
    assets: str = "assets"
    game: str = "game"


class ProjectManifest(BaseModel):
    """
    Manifest defining a RigMate-managed character/rig project.
    Strict constraints:
    - database_mode must be 'none' (local-first file-based architecture)
    - rigmate_account_required must be False (zero cloud accounts needed)
    """
    schema_version: str = "1.0.0"
    project_id: str
    display_name: str
    mode: ProjectMode = ProjectMode.MODE_3D
    database_mode: Literal["none"] = "none"
    rigmate_account_required: Literal[False] = False
    roots: ProjectRoots = Field(default_factory=ProjectRoots)
    target_platforms: List[str] = Field(default_factory=lambda: ["godot4"])
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    spec_version: str = "1.0.0"
    compatibility_profile_ref: Optional[str] = None
    custom_metadata: Dict[str, str] = Field(default_factory=dict)

    @field_validator("database_mode")
    @classmethod
    def validate_database_mode(cls, v: str) -> str:
        if v != "none":
            raise ValueError(f"Unsupported database_mode: '{v}'. RigMate is local file-based only ('none').")
        return v

    @field_validator("rigmate_account_required")
    @classmethod
    def validate_account_required(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError("RigMate does not require cloud accounts. rigmate_account_required must be False.")
        return v

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("project_id cannot be empty")
        return clean
