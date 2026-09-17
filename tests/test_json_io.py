"""Unit tests for durable JSON and JSONL persistence primitives."""

from pathlib import Path
import pytest
from rigmate.storage.json_io import (
    read_json,
    write_json_atomic,
    append_jsonl,
    iter_jsonl,
    read_jsonl_all,
    JsonlCorruptionError,
)


def test_json_io_atomic_write_and_read(tmp_path):
    f = tmp_path / "test.json"
    data = {"project": "RigMate", "unicode_text": "Chiến binh 3D ⚔️"}

    write_json_atomic(f, data)
    assert f.is_file()

    loaded = read_json(f)
    assert loaded["project"] == "RigMate"
    assert loaded["unicode_text"] == "Chiến binh 3D ⚔️"


def test_jsonl_append_and_ordering(tmp_path):
    f = tmp_path / "journal.jsonl"
    r1 = {"seq": 0, "event": "init"}
    r2 = {"seq": 1, "event": "start", "label": "Tác vụ 1"}
    r3 = {"seq": 2, "event": "done"}

    append_jsonl(f, r1)
    append_jsonl(f, r2)
    append_jsonl(f, r3)

    records = read_jsonl_all(f)
    assert len(records) == 3
    assert [r["seq"] for r in records] == [0, 1, 2]
    assert records[1]["label"] == "Tác vụ 1"


def test_jsonl_tolerates_truncated_final_line(tmp_path):
    f = tmp_path / "crashed_journal.jsonl"
    # Write 2 good lines and 1 half-written crashed line
    content = '{"seq": 0}\n{"seq": 1}\n{"seq": 2, "broken": "tru'
    f.write_text(content, encoding="utf-8")

    # With tolerate_truncated_final_line=True (default), recovers first 2 lines
    records = list(iter_jsonl(f, tolerate_truncated_final_line=True))
    assert len(records) == 2
    assert records[0]["seq"] == 0
    assert records[1]["seq"] == 1

    # With tolerate_truncated_final_line=False, raises exception
    with pytest.raises(JsonlCorruptionError):
        list(iter_jsonl(f, tolerate_truncated_final_line=False))


def test_jsonl_rejects_middle_corruption(tmp_path):
    f = tmp_path / "middle_corrupted.jsonl"
    content = '{"seq": 0}\n{CORRUPTED MIDDLE LINE}\n{"seq": 2}\n'
    f.write_text(content, encoding="utf-8")

    with pytest.raises(JsonlCorruptionError) as exc_info:
        list(iter_jsonl(f, tolerate_truncated_final_line=True))
    assert exc_info.value.line_number == 2
