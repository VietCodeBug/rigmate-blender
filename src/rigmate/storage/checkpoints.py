"""Content-addressed checkpoint engine for RigMate V1.

Layout:
  <storage_root>/
    checkpoints/<checkpoint_id>/manifest.json
    blobs/<prefix>/<sha256>

Features:
- Preflight disk budget verification before creation
- Content-addressed deduplication of files
- Streaming SHA-256 chunk hashing (no large files in RAM)
- Atomic manifest persistence
- Verified non-destructive restore to copy (<name>.recovered.<timestamp>.<ext>)
- Integration with retention calculator
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
from rigmate.core.checkpoints import CheckpointFileEntry, CheckpointManifest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.file_hash import sha256_file, file_size, verify_sha256
from rigmate.core.path_safety import require_within_root, safe_relative_path
from rigmate.core.time_utils import to_utc_iso, utc_now
from rigmate.storage.disk_budget import check_path_disk_budget
from rigmate.storage.json_io import read_json, write_json_atomic
from rigmate.storage.retention import (
    CheckpointMetadata,
    RetentionPolicy,
    calculate_retention,
)


class CheckpointEngine:
    """
    Manages content-addressed blob storage and manifests for project checkpoints.
    """

    def __init__(self, storage_root: Union[str, Path]):
        self.storage_root = Path(storage_root).resolve()
        self.checkpoints_dir = self.storage_root / "checkpoints"
        self.blobs_dir = self.storage_root / "blobs"

    def _blob_path(self, sha256_hex: str) -> Path:
        clean = sha256_hex.lower()
        prefix = clean[:2]
        return self.blobs_dir / prefix / clean

    def create_checkpoint(
        self,
        checkpoint_id: str,
        project_id: str,
        job_id: str,
        project_root: Union[str, Path],
        file_paths: List[Union[str, Path]],
        source_revision: str,
        reason: str = "pre-mutation backup",
        protected: bool = False,
    ) -> CheckpointManifest:
        """
        Create a durable, verified checkpoint from explicitly authorized file paths.
        Enforces path safety and disk budget before copying.
        """
        p_root = Path(project_root).resolve()
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)

        manifest_dir = self.checkpoints_dir / checkpoint_id
        manifest_file = manifest_dir / "manifest.json"

        # 1. Path safety and size aggregation
        canonical_files: List[Path] = []
        total_source_bytes: int = 0
        for f in file_paths:
            # Enforce that target is inside project root
            canon = require_within_root(f, p_root)
            if not canon.is_file():
                raise FileNotFoundError(f"Checkpoint source file does not exist: '{canon}'")
            canonical_files.append(canon)
            total_source_bytes += file_size(canon)

        # 2. Preflight disk budget check
        budget = check_path_disk_budget(
            self.storage_root,
            required_bytes=total_source_bytes,
            safety_margin_bytes=10 * 1024 * 1024,  # 10 MB margin
        )
        if not budget.allowed:
            raise RigMateError(
                f"Insufficient disk space for checkpoint: required {budget.required_total} bytes, available {budget.available} bytes",
                code=RigMateErrorCode.DISK_BUDGET_EXCEEDED,
                details={
                    "required_bytes": total_source_bytes,
                    "available_bytes": budget.available,
                    "shortfall": budget.shortfall,
                },
            )

        manifest = CheckpointManifest(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            job_id=job_id,
            created_at=to_utc_iso(),
            reason=reason,
            protected=protected,
            source_revision=source_revision,
            files=[],
            total_bytes=total_source_bytes,
            complete=False,
            verified_at=None,
        )

        try:
            # Write uncompleted manifest first
            write_json_atomic(manifest_file, manifest.model_dump())

            entries: List[CheckpointFileEntry] = []
            # 3. Stream blobs into content-addressed store
            for src_path in canonical_files:
                f_hash = sha256_file(src_path)
                f_size = file_size(src_path)
                rel_path = str(safe_relative_path(src_path, p_root)).replace("\\", "/")

                b_path = self._blob_path(f_hash)
                b_path.parent.mkdir(parents=True, exist_ok=True)

                if not b_path.exists():
                    # Copy and verify hash
                    shutil.copy2(src_path, b_path)
                    verify_sha256(b_path, f_hash)

                blob_ref = f"{b_path.parent.name}/{b_path.name}"
                entries.append(
                    CheckpointFileEntry(
                        relative_path=rel_path,
                        size=f_size,
                        sha256=f_hash,
                        blob_ref=blob_ref,
                    )
                )

            # 4. Finalize and verify manifest
            manifest.files = entries
            manifest.complete = True
            manifest.verified_at = to_utc_iso()
            write_json_atomic(manifest_file, manifest.model_dump())
            return manifest

        except Exception as e:
            # Mark incomplete/failed
            if manifest_file.exists():
                manifest.complete = False
                manifest.verified_at = None
                try:
                    write_json_atomic(manifest_file, manifest.model_dump())
                except Exception:
                    pass
            if isinstance(e, RigMateError):
                raise
            raise RigMateError(
                f"Checkpoint creation failed: {e}",
                code=RigMateErrorCode.CHECKPOINT_FAILED,
                cause=e,
            ) from e

    def load_manifest(self, checkpoint_id: str) -> CheckpointManifest:
        """Load and parse checkpoint manifest."""
        manifest_file = self.checkpoints_dir / checkpoint_id / "manifest.json"
        if not manifest_file.is_file():
            raise RigMateError(
                f"Checkpoint manifest not found: '{checkpoint_id}'",
                code=RigMateErrorCode.CHECKPOINT_REQUIRED,
                details={"checkpoint_id": checkpoint_id},
            )
        data = read_json(manifest_file)
        return CheckpointManifest(**data)

    def restore_to_copy(
        self,
        checkpoint_id: str,
        project_root: Union[str, Path],
        output_suffix: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Restore checkpoint files to non-destructive copy paths.
        e.g. character.blend -> character.recovered.<timestamp>.blend.
        Verifies restored SHA-256 against manifest hashes.
        Returns mapping: relative_original_path -> restored_absolute_path.
        """
        manifest = self.load_manifest(checkpoint_id)
        if not manifest.complete:
            raise RigMateError(
                f"Cannot restore from incomplete checkpoint: '{checkpoint_id}'",
                code=RigMateErrorCode.CHECKPOINT_INCOMPLETE,
                details={"checkpoint_id": checkpoint_id},
            )

        p_root = Path(project_root).resolve()
        restored_files: Dict[str, str] = {}
        ts = utc_now().strftime("%Y%m%d_%H%M%S")
        suffix = output_suffix or f"recovered.{ts}"

        for entry in manifest.files:
            b_path = self.blobs_dir / entry.blob_ref
            if not b_path.is_file():
                raise RigMateError(
                    f"Blob missing for checkpoint file '{entry.relative_path}': '{b_path}'",
                    code=RigMateErrorCode.CHECKPOINT_FAILED,
                    details={"blob_ref": entry.blob_ref},
                )

            # Build non-destructive destination
            orig_dest = p_root / Path(entry.relative_path)
            # character.blend -> character.recovered.<ts>.blend
            ext = orig_dest.suffix
            stem = orig_dest.stem
            dest_name = f"{stem}.{suffix}{ext}"
            restore_dest = orig_dest.parent / dest_name

            restore_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(b_path, restore_dest)

            # Strict verification of restored file
            verify_sha256(restore_dest, entry.sha256)
            restored_files[entry.relative_path] = str(restore_dest)

        return restored_files

    def evaluate_retention(
        self,
        active_job_checkpoint_ids: Optional[List[str]] = None,
        policy: Optional[RetentionPolicy] = None,
    ) -> List[str]:
        """
        Evaluate which checkpoints can be safely cleaned up using pure retention calculator.
        Never marks pinned, active-job, or recovery-required checkpoints as deletion candidates.
        """
        active_ids = set(active_job_checkpoint_ids or [])
        pol = policy or RetentionPolicy()

        metas: List[CheckpointMetadata] = []
        if not self.checkpoints_dir.exists():
            return []

        for c_dir in self.checkpoints_dir.iterdir():
            m_file = c_dir / "manifest.json"
            if m_file.is_file():
                try:
                    m = CheckpointManifest(**read_json(m_file))
                    metas.append(
                        CheckpointMetadata(
                            checkpoint_id=m.checkpoint_id,
                            created_at=m.created_at,
                            size_bytes=m.total_bytes,
                            is_pinned=m.protected,
                            is_required_by_active_job=(m.checkpoint_id in active_ids),
                            is_newest_pre_mutation=False,
                        )
                    )
                except Exception:
                    continue

        decision = calculate_retention(metas, pol)
        return decision.candidates_for_deletion
