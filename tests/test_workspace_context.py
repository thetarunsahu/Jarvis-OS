from __future__ import annotations

import pytest

from core.brain import Brain
from core.workspace import WorkspaceContext
from tools.tool_registry import ToolRegistry


class FakeProvider:
    def generate(self, *args, **kwargs):
        return "unused"

    def clear_history(self) -> None:
        pass


def test_workspace_resolves_relative_paths_inside_root(tmp_path) -> None:
    workspace = WorkspaceContext(tmp_path)
    nested = tmp_path / "src"
    nested.mkdir()

    assert workspace.resolve("src") == nested.resolve()


def test_workspace_rejects_path_escape(tmp_path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = WorkspaceContext(root)

    with pytest.raises(PermissionError, match="outside the JARVIS workspace"):
        workspace.resolve("../secret.txt")


def test_workspace_requires_existing_directory(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Workspace does not exist"):
        WorkspaceContext(tmp_path / "missing")

    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError, match="not a directory"):
        WorkspaceContext(file_path)


def test_brain_binds_file_tools_to_explicit_workspace(tmp_path) -> None:
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "src").mkdir()

    brain = Brain(
        provider=FakeProvider(),
        tools=ToolRegistry(),
        workspace=WorkspaceContext(tmp_path),
    )

    read_result = brain.execute_tool("read_text_file", {"path": "note.txt"})
    list_result = brain.execute_tool("list_files", {"directory": "."})

    assert read_result["ok"] is True
    assert read_result["data"]["content"] == "hello"
    assert list_result["ok"] is True
    assert {entry["name"] for entry in list_result["data"]["entries"]} == {
        "note.txt",
        "src",
    }
