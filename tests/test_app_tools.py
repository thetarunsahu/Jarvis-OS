from pathlib import Path

import pytest

from tools.app_tools import AppTools
from tools.tool_registry import ToolRegistry


def test_open_app_resolves_and_launches_without_shell(monkeypatch):
    launched = []

    monkeypatch.setattr(
        AppTools,
        "_resolve_application",
        classmethod(lambda cls, name: "C:/Fake/App.exe"),
    )
    monkeypatch.setattr(
        AppTools,
        "_launch",
        staticmethod(lambda executable, arguments=None: launched.append((executable, arguments))),
    )

    result = AppTools.open_app("Fake App")

    assert launched == [("C:/Fake/App.exe", None)]
    assert result["app"] == "Fake App"
    assert result["resolved"] == "C:/Fake/App.exe"


def test_open_project_requires_existing_directory(tmp_path: Path):
    file_path = tmp_path / "not-a-project.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Project path must be a directory"):
        AppTools.open_project(str(file_path))


def test_desktop_actions_require_confirmation():
    metadata = {
        item["name"]: item["permission"]
        for item in ToolRegistry().get_tool_metadata()
    }

    assert metadata["list_running_apps"] == "safe"
    assert metadata["open_app"] == "confirm"
    assert metadata["open_path"] == "confirm"
    assert metadata["open_project"] == "confirm"
