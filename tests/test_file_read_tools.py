from __future__ import annotations

import pytest

from core.brain import Brain
from tools.file_tools import FileTools
from tools.tool_registry import ToolRegistry


class FakeProvider:
    def generate(self, *args, **kwargs):
        return "unused"

    def clear_history(self) -> None:
        pass


def test_read_text_file_returns_structured_content(tmp_path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("hello jarvis", encoding="utf-8")

    result = FileTools.read_text_file(str(target))

    assert result["content"] == "hello jarvis"
    assert result["size_bytes"] == len("hello jarvis".encode("utf-8"))
    assert result["truncated"] is False
    assert result["path"].endswith("note.txt")


def test_read_text_file_rejects_oversized_file(tmp_path) -> None:
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        FileTools.read_text_file(str(target), max_bytes=3)


def test_read_text_file_rejects_binary_data(tmp_path) -> None:
    target = tmp_path / "binary.bin"
    target.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(ValueError, match="UTF-8"):
        FileTools.read_text_file(str(target))


def test_brain_registers_read_text_file_as_safe_tool() -> None:
    registry = ToolRegistry()
    brain = Brain(provider=FakeProvider(), tools=registry)

    metadata = {item["name"]: item for item in brain.tools.get_tool_metadata()}

    assert metadata["read_text_file"]["permission"] == "safe"
