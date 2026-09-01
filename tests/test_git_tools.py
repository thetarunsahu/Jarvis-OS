from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.workspace import WorkspaceContext
from tools.git_extension import register_git_tools
from tools.git_tools import GitTools
from tools.tool_registry import ToolRegistry


def test_git_status_parses_branch_counts_and_bounds_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=(
                "## feature/test...origin/feature/test [ahead 2, behind 1]\n"
                "M  staged.py\n"
                " M unstaged.py\n"
                "?? new.txt\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = GitTools.inspect_status(tmp_path, max_entries=2)

    assert result["branch"] == "feature/test"
    assert result["upstream"] == "origin/feature/test"
    assert result["ahead"] == 2
    assert result["behind"] == 1
    assert result["clean"] is False
    assert result["staged_count"] == 1
    assert result["unstaged_count"] == 1
    assert result["untracked_count"] == 1
    assert result["total_count"] == 3
    assert result["returned_count"] == 2
    assert result["truncated"] is True


def test_git_status_is_clean_when_no_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="## main\n",
            stderr="",
        ),
    )

    result = GitTools.inspect_status(tmp_path)

    assert result["branch"] == "main"
    assert result["clean"] is True
    assert result["entries"] == []


def test_git_status_rejects_non_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository (or any parent up to mount point)",
        ),
    )

    with pytest.raises(ValueError, match="not a Git repository"):
        GitTools.inspect_status(tmp_path)


def test_git_status_uses_bounded_shell_free_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["command"] = args[0]
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="## main\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    GitTools.inspect_status(tmp_path, timeout_seconds=7)

    assert captured["command"][:3] == ["git", "-C", str(tmp_path.resolve())]
    assert captured["shell"] is False
    assert captured["timeout"] == 7


def test_git_diff_returns_bounded_unstaged_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    patch = "diff --git a/a.txt b/a.txt\n+" + ("x" * 100)

    def fake_run(*args, **kwargs):
        captured["command"] = args[0]
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=patch,
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = GitTools.inspect_diff(tmp_path, max_bytes=48, timeout_seconds=6)

    assert result["staged"] is False
    assert result["truncated"] is True
    assert result["returned_bytes"] <= 48
    assert result["total_bytes"] == len(patch.encode("utf-8"))
    assert "--cached" not in captured["command"]
    assert "--no-ext-diff" in captured["command"]
    assert captured["shell"] is False
    assert captured["timeout"] == 6


def test_git_diff_supports_staged_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["command"] = args[0]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="diff --git a/a.txt b/a.txt\n+hello\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = GitTools.inspect_diff(tmp_path, staged=True)

    assert result["staged"] is True
    assert result["truncated"] is False
    assert "--cached" in captured["command"]


def test_git_diff_rejects_oversized_requested_limit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_bytes"):
        GitTools.inspect_diff(tmp_path, max_bytes=GitTools.MAX_DIFF_BYTES + 1)


def test_git_status_and_diff_tools_are_registered_safe(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_git_tools(registry, WorkspaceContext(tmp_path))

    metadata = {item["name"]: item for item in registry.get_tool_metadata()}

    assert metadata["git_status"]["permission"] == "safe"
    assert metadata["git_diff"]["permission"] == "safe"
