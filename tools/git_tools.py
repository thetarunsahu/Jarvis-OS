from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from core.workspace import WorkspaceContext


class GitTools:
    """Bounded, read-only Git inspection helpers scoped to a JARVIS workspace."""

    DEFAULT_TIMEOUT_SECONDS = 5
    MAX_STATUS_ENTRIES = 200

    @staticmethod
    def _run_git(
        workspace: WorkspaceContext,
        args: list[str],
        *,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> subprocess.CompletedProcess[str]:
        if timeout_seconds < 1 or timeout_seconds > 30:
            raise ValueError("timeout_seconds must be between 1 and 30")

        try:
            return subprocess.run(
                ["git", "-C", str(workspace.root), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as error:
            raise RuntimeError("Git executable was not found on this system.") from error
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(
                f"Git command exceeded {timeout_seconds} second timeout."
            ) from error

    @classmethod
    def inspect_status(
        cls,
        workspace_root: str | Path = ".",
        max_entries: int = MAX_STATUS_ENTRIES,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Return structured, bounded status for the Git repo at the workspace root."""
        if max_entries < 1 or max_entries > cls.MAX_STATUS_ENTRIES:
            raise ValueError(
                f"max_entries must be between 1 and {cls.MAX_STATUS_ENTRIES}"
            )

        workspace = WorkspaceContext(workspace_root)
        result = cls._run_git(
            workspace,
            ["status", "--porcelain=v1", "--branch", "--untracked-files=normal"],
            timeout_seconds=timeout_seconds,
        )

        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            lowered = message.lower()
            if "not a git repository" in lowered:
                raise ValueError("Active JARVIS workspace is not a Git repository.")
            raise RuntimeError(
                message or f"git status failed with exit code {result.returncode}."
            )

        lines = result.stdout.splitlines()
        branch_line = lines[0] if lines and lines[0].startswith("## ") else ""
        status_lines = lines[1:] if branch_line else lines

        branch: str | None = None
        upstream: str | None = None
        ahead = 0
        behind = 0

        if branch_line:
            branch_info = branch_line[3:]
            head_part, _, tracking_part = branch_info.partition("...")
            branch = head_part.strip() or None
            if tracking_part:
                upstream_part, _, divergence = tracking_part.partition(" ")
                upstream = upstream_part.strip() or None
                divergence = divergence.strip().strip("[]")
                for token in divergence.split(","):
                    token = token.strip()
                    if token.startswith("ahead "):
                        try:
                            ahead = int(token.removeprefix("ahead "))
                        except ValueError:
                            ahead = 0
                    elif token.startswith("behind "):
                        try:
                            behind = int(token.removeprefix("behind "))
                        except ValueError:
                            behind = 0

        entries: list[dict[str, str]] = []
        staged = 0
        unstaged = 0
        untracked = 0

        for line in status_lines:
            if len(line) < 3:
                continue
            index_state = line[0]
            worktree_state = line[1]
            path = line[3:]

            if index_state == "?" and worktree_state == "?":
                untracked += 1
                kind = "untracked"
            else:
                if index_state not in {" ", "?"}:
                    staged += 1
                if worktree_state not in {" ", "?"}:
                    unstaged += 1
                kind = "tracked_change"

            if len(entries) < max_entries:
                entries.append(
                    {
                        "path": path,
                        "index": index_state,
                        "worktree": worktree_state,
                        "kind": kind,
                    }
                )

        total_entries = len(status_lines)
        return {
            "repository_root": str(workspace.root),
            "branch": branch,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "clean": total_entries == 0,
            "staged_count": staged,
            "unstaged_count": unstaged,
            "untracked_count": untracked,
            "entries": entries,
            "returned_count": len(entries),
            "total_count": total_entries,
            "truncated": total_entries > len(entries),
        }
