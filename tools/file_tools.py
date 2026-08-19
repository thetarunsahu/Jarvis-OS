from __future__ import annotations

from pathlib import Path


class FileTools:
    """Read-only file inspection primitives used by JARVIS tools."""

    MAX_TEXT_BYTES = 256 * 1024

    @staticmethod
    def list_files(directory: str = ".") -> str:
        path = Path(directory)

        if not path.exists():
            return "Directory does not exist."

        items = []

        for item in path.iterdir():
            if item.name.startswith("."):
                continue

            if item.is_dir():
                items.append(f"[DIR]  {item.name}")
            else:
                items.append(f"[FILE] {item.name}")

        if not items:
            return "Directory is empty."

        return "\n".join(sorted(items))

    @staticmethod
    def read_text_file(path: str, max_bytes: int = MAX_TEXT_BYTES) -> dict[str, object]:
        """Read a UTF-8 text file with a hard size bound.

        The bound keeps model/tool observations predictable and prevents a single
        accidental read from pulling a very large file into the agent context.
        """
        file_path = Path(path).expanduser()

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
            "path": str(file_path.resolve()),
            "size_bytes": size_bytes,
            "content": content,
            "truncated": False,
        }
