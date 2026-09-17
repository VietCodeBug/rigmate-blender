"""Checkpoint domain models for RigMate V1.

Defines:
- CheckpointFileEntry: metadata of a preserved file
- CheckpointManifest: durable manifest model persisted to .rigmate/checkpoints/<checkpoint_id>/manifest.json
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso


class CheckpointFileEntry(BaseModel):
    """Entry describing a preserved file inside a checkpoint."""
    relative_path: str
    size: int = Field(ge=0)
    sha256: str
    blob_ref: str

    @model_validator(mode="after")
    def validate_file_entry(self) -> "CheckpointFileEntry":
        if not self.relative_path or not self.relative_path.strip():
            raise ValueError("relative_path must be a non-empty string")
        if not self.sha256 or len(self.sha256) != 64:
            raise ValueError("sha256 must be a 64-char hex string")
        if not self.blob_ref or not self.blob_ref.strip():
            raise ValueError("blob_ref must be a non-empty string")
        return self


class CheckpointManifest(BaseModel):
    """
    Durable checkpoint manifest.
    Persisted to .rigmate/checkpoints/<checkpoint_id>/manifest.json.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    checkpoint_id: str
    project_id: str
    job_id: str
    created_at: str = Field(default_factory=to_utc_iso)

    reason: str = "pre-mutation backup"
    protected: bool = False
    source_revision: str

    files: List[CheckpointFileEntry] = Field(default_factory=list)
    total_bytes: int = Field(default=0, ge=0)

    complete: bool = False
    verified_at: Optional[str] = None

    @model_validator(mode="after")
    def validate_manifest(self) -> "CheckpointManifest":
        for field_name in [
            "checkpoint_id",
            "project_id",
            "job_id",
            "source_revision",
        ]:
            val = getattr(self, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"CheckpointManifest field '{field_name}' must be a non-empty string")

        parse_utc_iso(self.created_at)
        if self.verified_at:
            parse_utc_iso(self.verified_at)

        if self.complete and not self.verified_at:
            raise ValueError("Completed CheckpointManifest requires verified_at timestamp")

        return self
