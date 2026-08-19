from __future__ import annotations

from pathlib import Path


class FileTools:
    """Read-only file inspection primitives used by JARVIS tools."""

    MAX_TEXT_BYTES = 256 * 1024
    MAX_LIST_ENTRIES = 200

    @staticmethod
    def list_files(
        directory: str = ".",
        max_entries: int = MAX_LIST_ENTRIES,
        *,
        workspace_root: str | Path | None = None,
    ) -> dict[str, object]:
        """List a directory inside the active workspace using bounded structured output."""
        path = FileTools._resolve_workspace_file(directory, workspace_root)

        if max_entries < 1 or max_entries > FileTools.MAX_LIST_ENTRIES:
            raise ValueError(
                f"max_entries must be between 1 and {FileTools.MAX_LIST_ENTRIES}."
            )
        if not path.exists():
            raise FileNotFoundError(f"Directory does not exist: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        visible_items = sorted(
            (item for item in path.iterdir() if not item.name.startswith(".")),
            key=lambda item: item.name.casefold(),
        )
        selected_items = visible_items[:max_entries]
        entries = [
            {
                "name": item.name,
                "path": str(item.relative_to(path)),
                "type": "directory" if item.is_dir() else "file",
            }
            for item in selected_items
        ]

        return {
            "path": str(path),
            "entries": entries,
            "count": len(entries),
            "total_visible": len(visible_items),
            "truncated": len(visible_items) > max_entries,
        }

    @staticmethod
    def _resolve_workspace_file(
        path: str,
        workspace_root: str | Path | None = None,
    ) -> Path:
        """Resolve a file path and reject traversal outside the active workspace."""
        root = Path(workspace_root or Path.cwd()).expanduser().resolve()
        candidate = Path(path).expanduser()

        if not candidate.is_absolute():
            candidate = root / candidate

        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise PermissionError(
                f"Path is outside the JARVIS workspace: {resolved}"
            ) from error

        return resolved

    @staticmethod
    def read_text_file(
        path: str,
        max_bytes: int = MAX_TEXT_BYTES,
        *,
        workspace_root: str | Path | None = None,
    ) -> dict[str, object]:
        """Read a UTF-8 text file inside the active workspace with a hard size bound.

        The workspace boundary prevents a model-supplied path from inspecting
        arbitrary files elsewhere on the computer. The size bound keeps model/tool
        observations predictable and prevents a single accidental read from pulling
        a very large file into the agent context.
        """
        file_path = FileTools._resolve_workspace_file(path, workspace_root)

        if max_bytes < 1 or max_bytes > FileTools.MAX_TEXT_BYTES:
            raise ValueError(
                f"max_bytes must be between 1 and {FileTools.MAX_TEXT_BYTES}."
            )
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {file_path}")

        size_bytes = file_path.stat().st_size
        if size_bytes > max_bytes:
            raise ValueError(
                f"File is too large to read safely ({size_bytes} bytes; limit {max_bytes})."
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("File is not valid UTF-8 text.") from error

        return {
            "path": str(file_path),
            "size_bytes": size_bytes,
            "content": content,
            "truncated": False,
        }
