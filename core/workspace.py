from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceContext:
    """Defines the filesystem boundary for JARVIS computer-control tools."""

    root: Path

    def __init__(self, root: str | Path) -> None:
        resolved_root = Path(root).expanduser().resolve()
        if not resolved_root.exists():
            raise FileNotFoundError(f"Workspace does not exist: {resolved_root}")
        if not resolved_root.is_dir():
            raise NotADirectoryError(f"Workspace root is not a directory: {resolved_root}")
        object.__setattr__(self, "root", resolved_root)

    @classmethod
    def from_cwd(cls) -> "WorkspaceContext":
        return cls(Path.cwd())

    def resolve(self, path: str | Path) -> Path:
        """Resolve a path and reject traversal outside the workspace root."""
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate

        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise PermissionError(
                f"Path is outside the JARVIS workspace: {resolved}"
            ) from error

        return resolved
