import os
from pathlib import Path


class FileTools:
    """Read-only filesystem helpers constrained to configured roots."""

    MAX_READ_CHARS = 100_000

    @classmethod
    def project_root(cls):
        return Path(__file__).resolve().parents[1]

    @classmethod
    def allowed_roots(cls):
        configured = os.getenv("JARVIS_ALLOWED_PATHS", "").strip()
        if configured:
            candidates = [item for item in configured.split(os.pathsep) if item]
        else:
            # File-index roots are already user-selected and are reasonable
            # read-only roots when a separate allowlist is not configured.
            indexed = os.getenv("JARVIS_INDEX_PATHS", "").strip()
            candidates = [item for item in indexed.split(os.pathsep) if item] if indexed else []

        candidates.append(str(cls.project_root()))

        roots = []
        for item in candidates:
            try:
                path = Path(item).expanduser().resolve()
            except OSError:
                continue
            if path.exists() and path not in roots:
                roots.append(path)
        return roots

    @classmethod
    def _resolve_allowed(cls, value="."):
        raw = Path(value).expanduser()
        if raw.is_absolute():
            path = raw.resolve()
        else:
            path = (cls.project_root() / raw).resolve()

        for root in cls.allowed_roots():
            if path == root or root in path.parents:
                return path

        raise PermissionError(
            f"Path is outside JARVIS allowed roots: {path}"
        )

    @classmethod
    def list_files(cls, directory="."):
        try:
            path = cls._resolve_allowed(directory)
        except (OSError, PermissionError) as error:
            return f"File access denied: {error}"

        if not path.exists():
            return "Directory does not exist."
        if not path.is_dir():
            return "Path is not a directory."

        items = []
        try:
            for item in path.iterdir():
                if item.name.startswith("."):
                    continue

                if item.is_dir():
                    items.append(f"[DIR]  {item.name}")
                else:
                    items.append(f"[FILE] {item.name}")
        except OSError as error:
            return f"Could not list directory: {error}"

        if not items:
            return "Directory is empty."

        return "\n".join(sorted(items))

    @classmethod
    def read_text_file(cls, path, max_chars=20_000):
        try:
            file_path = cls._resolve_allowed(path)
        except (OSError, PermissionError) as error:
            return f"File access denied: {error}"

        if not file_path.exists():
            return "File does not exist."
        if not file_path.is_file():
            return "Path is not a file."

        limit = max(1, min(cls.MAX_READ_CHARS, int(max_chars)))
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            return f"Could not read file: {error}"

        if len(text) <= limit:
            return text

        return (
            text[:limit]
            + f"\n\n[TRUNCATED: showing first {limit} of {len(text)} characters]"
        )

    @classmethod
    def file_info(cls, path):
        try:
            file_path = cls._resolve_allowed(path)
        except (OSError, PermissionError) as error:
            return {"error": f"File access denied: {error}"}

        if not file_path.exists():
            return {"error": "Path does not exist."}

        try:
            stat = file_path.stat()
        except OSError as error:
            return {"error": f"Could not inspect path: {error}"}

        return {
            "path": str(file_path),
            "name": file_path.name,
            "type": "directory" if file_path.is_dir() else "file",
            "suffix": file_path.suffix.lower() if file_path.is_file() else "",
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
        }
