"""Unit tests for path containment and safety utilities."""

from pathlib import Path
import pytest
from rigmate.core.path_safety import (
    canonicalize_path,
    is_within_root,
    require_within_root,
    safe_relative_path,
    PathOutsideRootError,
)


def test_path_safety_normal_child(tmp_path):
    root = tmp_path / "project_root"
    root.mkdir()
    child = root / "models" / "character.blend"

    assert is_within_root(child, root) is True
    req = require_within_root(child, root)
    assert req == child.resolve()
    rel = safe_relative_path(child, root)
    assert rel == Path("models/character.blend")


def test_path_safety_nested_subdirectories(tmp_path):
    root = tmp_path / "root"
    nested = root / "a" / "b" / "c" / "d" / "mesh.obj"
    assert is_within_root(nested, root) is True
    rel = safe_relative_path(nested, root)
    assert rel == Path("a/b/c/d/mesh.obj")


def test_path_safety_traversal_escape_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    escape_target = root / ".." / "outside.txt"

    assert is_within_root(escape_target, root) is False
    with pytest.raises(PathOutsideRootError):
        require_within_root(escape_target, root)
    with pytest.raises(PathOutsideRootError):
        safe_relative_path(escape_target, root)


def test_path_safety_sibling_root_rejected(tmp_path):
    root_a = tmp_path / "project_a"
    root_b = tmp_path / "project_b"
    root_a.mkdir()
    root_b.mkdir()
    file_in_b = root_b / "secret.json"

    assert is_within_root(file_in_b, root_a) is False
    with pytest.raises(PathOutsideRootError):
        require_within_root(file_in_b, root_a)


def test_path_safety_spaces_and_unicode_paths(tmp_path):
    root = tmp_path / "rigmate workspace" / "dự_án_mẫu_3d"
    root.mkdir(parents=True)
    child = root / "nhân vật" / "tư thế 01.gltf"

    assert is_within_root(child, root) is True
    req = require_within_root(child, root)
    assert req == child.resolve()
    rel = safe_relative_path(child, root)
    assert rel == Path("nhân vật/tư thế 01.gltf")


def test_path_safety_exact_root():
    root = Path("D:/Ark_3/RigMate").resolve()
    assert is_within_root(root, root) is True
    assert safe_relative_path(root, root) == Path(".")
