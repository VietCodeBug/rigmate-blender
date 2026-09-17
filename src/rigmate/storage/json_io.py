"""Durable JSON and JSON Lines (JSONL) persistence primitives.

Features:
- Atomic JSON write using temporary files on the same filesystem
- Preserved append-order and recovery for JSONL streams
- Crash tolerance: tolerates ONLY a truncated final line in JSONL
- Strict reporting for middle-of-stream corruption (never silently ignored)
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union


class JsonIoError(IOError):
    """Base error for JSON/JSONL I/O failures."""
    pass


class JsonlCorruptionError(JsonIoError):
    """Raised when JSONL contains corruption that cannot be safely skipped."""

    def __init__(self, message: str, line_number: int, line_content: str):
        super().__init__(f"Line {line_number}: {message}")
        self.line_number = line_number
        self.line_content = line_content


def read_json(path: Union[str, Path]) -> Any:
    """Read and deserialize JSON file using UTF-8."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Write data to JSON file atomically via a temporary file in the same directory.
    Cleans up temporary file upon error.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    temp_file: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=str(target.parent),
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        ) as f:
            temp_file = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        temp_file.replace(target)
    except Exception as e:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        raise JsonIoError(f"Atomic JSON write failed for '{target}': {e}") from e


def append_jsonl(path: Union[str, Path], record: Dict[str, Any]) -> None:
    """
    Append a single dictionary record to a JSONL file.
    Ensures UTF-8 and trailing newline.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(target, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def iter_jsonl(path: Union[str, Path], tolerate_truncated_final_line: bool = True) -> Iterator[Dict[str, Any]]:
    """
    Yield parsed records from a JSONL file sequentially.
    
    Crash-tolerance behavior:
    - If tolerate_truncated_final_line is True, an EOF truncation on the very LAST line
      is logged/tolerated (common after process crash/SIGKILL).
    - Any corruption in the MIDDLE of the file raises JsonlCorruptionError immediately.
    """
    target = Path(path)
    if not target.is_file():
        return

    with open(target, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        try:
            yield json.loads(stripped)
        except json.JSONDecodeError as e:
            is_final_line = (idx == total_lines)
            if is_final_line and tolerate_truncated_final_line:
                # Crash occurred during final write; stop iteration safely
                break
            raise JsonlCorruptionError(
                f"Corrupted JSONL record ({e}): {stripped[:80]}",
                line_number=idx,
                line_content=stripped,
            ) from e


def read_jsonl_all(path: Union[str, Path], tolerate_truncated_final_line: bool = True) -> List[Dict[str, Any]]:
    """Read all records from JSONL into a list."""
    return list(iter_jsonl(path, tolerate_truncated_final_line=tolerate_truncated_final_line))
