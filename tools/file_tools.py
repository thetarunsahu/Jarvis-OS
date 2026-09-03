import os
from pathlib import Path


class FileTools:
    """Read-only filesystem helpers constrained to configured roots."""

    MAX_READ_CHARS = 100_000

    SENSITIVE_DIRECTORIES = {
        ".git",
        ".ssh",
        ".aws",
        ".azure",
        ".gnupg",
    }
    SENSITIVE_FILENAMES = {
        ".env",
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "secrets.json",
        "id_rsa",
        "id_ed25519",
    }
    SENSITIVE_SUFFIXES = {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
    }

    @classmethod
    def project_root(cls):
        return Path(__file__).resolve().parents[1]

    @classmethod
    def allowed_roots(cls):
        configured = os.getenv("JARVIS_ALLOWED_PATHS", "").strip()
        if configured:
            candidates = [item for item in configured.split(os.pathsep) if item]
        else:
            indexed = os.getenv("JARVIS_INDEX_PATHS", "").strip()
            candidates = (
                [item for item in indexed.split(os.pathsep) if item]
                if indexed
                else []
            )

        # JARVIS needs read access to its own source during development, but
        # sensitive files inside the project are denied separately below.
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
    def _is_sensitive(cls, path):
        lowered_parts = {part.lower() for part in path.parts}
        if lowered_parts.intersection(cls.SENSITIVE_DIRECTORIES):
            return True

        name = path.name.lower()
        if name == ".env.example":
            return False
        if name in cls.SENSITIVE_FILENAMES:
            return True
        if name.startswith(".env."):
            return True
        if path.suffix.lower() in cls.SENSITIVE_SUFFIXES:
            return True

        return False

    @classmethod
    def _resolve_allowed(cls, value=".", allow_sensitive=False):
        raw = Path(value).expanduser()
        if raw.is_absolute():
            path = raw.resolve()
        else:
            path = (cls.project_root() / raw).resolve()

        allowed = any(
            path == root or root in path.parents
            for root in cls.allowed_roots()
        )
        if not allowed:
            raise PermissionError(
                f"Path is outside JARVIS allowed roots: {path}"
            )

        if not allow_sensitive and cls._is_sensitive(path):
            raise PermissionError(
                "Path is protected because it may contain credentials or secrets."
            )

        return path

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
                if item.name.startswith(".") or cls._is_sensitive(item):
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
