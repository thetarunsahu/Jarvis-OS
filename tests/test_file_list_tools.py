from __future__ import annotations

import pytest

from tools.file_tools import FileTools


def test_list_files_returns_structured_sorted_entries(tmp_path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "A.txt").write_text("a", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / ".hidden").write_text("secret", encoding="utf-8")

    result = FileTools.list_files(workspace_root=tmp_path)

    assert result["count"] == 3
    assert result["total_visible"] == 3
    assert result["truncated"] is False
    assert [entry["name"] for entry in result["entries"]] == [
        "A.txt",
        "b.txt",
        "folder",
    ]
    assert [entry["type"] for entry in result["entries"]] == [
        "file",
        "file",
        "directory",
    ]


def test_list_files_is_bounded_and_reports_truncation(tmp_path) -> None:
    for index in range(3):
        (tmp_path / f"file-{index}.txt").write_text("x", encoding="utf-8")

    result = FileTools.list_files(max_entries=2, workspace_root=tmp_path)

    assert result["count"] == 2
    assert result["total_visible"] == 3
    assert result["truncated"] is True


def test_list_files_rejects_path_outside_workspace(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(PermissionError, match="outside the JARVIS workspace"):
        FileTools.list_files("../outside", workspace_root=workspace)


def test_list_files_rejects_non_directory_path(tmp_path) -> None:
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        FileTools.list_files("note.txt", workspace_root=tmp_path)
