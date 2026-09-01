import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class FileIndex:
    """SQLite-backed local file index with optional FTS5 search.

    JARVIS indexes only explicitly configured roots (or the project root as a
    development fallback). File contents are extracted only for small,
    text-like files. Binary files still contribute searchable metadata.
    """

    TEXT_EXTENSIONS = {
        ".txt", ".md", ".rst", ".py", ".java", ".c", ".cpp", ".h",
        ".hpp", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sql",
        ".csv", ".log", ".xml", ".sh", ".ps1", ".bat",
    }

    IGNORED_DIRECTORIES = {
        ".git", ".venv", ".venv-1", ".venv-2", "node_modules",
        "__pycache__", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
        "data", "logs", "Qwen3 8B",
    }

    def __init__(self, db_path=None, roots=None, max_text_bytes=None):
        project_root = Path(__file__).resolve().parents[1]
        configured_db = os.getenv("JARVIS_DB_PATH")
        self.db_path = Path(db_path or configured_db or project_root / "data" / "jarvis.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_text_bytes = int(
            max_text_bytes or os.getenv("JARVIS_FILE_MAX_TEXT_BYTES", 1_000_000)
        )
        self.roots = self._resolve_roots(roots, project_root)
        self.fts_enabled = False
        self._initialize()

    def _resolve_roots(self, roots, project_root):
        if roots:
            candidates = roots
        else:
            configured = os.getenv("JARVIS_INDEX_PATHS", "").strip()
            candidates = [item for item in configured.split(os.pathsep) if item] if configured else [project_root]

        resolved = []
        for item in candidates:
            path = Path(item).expanduser().resolve()
            if path.exists() and path not in resolved:
                resolved.append(path)
        return resolved

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS file_index (
                    path TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    extension TEXT,
                    size_bytes INTEGER NOT NULL,
                    modified_at REAL NOT NULL,
                    content TEXT,
                    indexed_at TEXT NOT NULL
                )
                """
            )
            try:
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS file_index_fts
                    USING fts5(path, name, content)
                    """
                )
                self.fts_enabled = True
            except sqlite3.OperationalError:
                self.fts_enabled = False

    def _is_ignored(self, path):
        return any(part in self.IGNORED_DIRECTORIES for part in path.parts)

    def _read_content(self, path, size_bytes):
        if path.suffix.lower() not in self.TEXT_EXTENSIONS:
            return None
        if size_bytes > self.max_text_bytes:
            return None
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

    def _upsert(self, connection, path):
        stat = path.stat()
        content = self._read_content(path, stat.st_size)
        path_text = str(path)

        connection.execute(
            """
            INSERT INTO file_index (
                path, name, extension, size_bytes, modified_at, content, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                extension = excluded.extension,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                content = excluded.content,
                indexed_at = excluded.indexed_at
            """,
            (
                path_text,
                path.name,
                path.suffix.lower(),
                stat.st_size,
                stat.st_mtime,
                content,
                utc_now_iso(),
            ),
        )

        if self.fts_enabled:
            connection.execute("DELETE FROM file_index_fts WHERE path = ?", (path_text,))
            connection.execute(
                "INSERT INTO file_index_fts (path, name, content) VALUES (?, ?, ?)",
                (path_text, path.name, content or ""),
            )

    def scan(self, roots=None):
        scan_roots = self._resolve_roots(roots, Path(__file__).resolve().parents[1]) if roots else self.roots
        indexed = 0
        skipped = 0
        discovered = set()

        with self._connect() as connection:
            for root in scan_roots:
                if root.is_file():
                    candidates = [root]
                else:
                    candidates = root.rglob("*")

                for path in candidates:
                    try:
                        if not path.is_file() or self._is_ignored(path):
                            continue
                        if any(part.startswith(".") for part in path.relative_to(root).parts):
                            continue

                        self._upsert(connection, path)
                        discovered.add(str(path))
                        indexed += 1
                    except (OSError, ValueError):
                        skipped += 1

            # Remove stale entries only inside roots scanned in this pass.
            rows = connection.execute("SELECT path FROM file_index").fetchall()
            for row in rows:
                candidate = Path(row["path"])
                in_scope = any(
                    candidate == root or root in candidate.parents
                    for root in scan_roots
                )
                if in_scope and row["path"] not in discovered:
                    connection.execute("DELETE FROM file_index WHERE path = ?", (row["path"],))
                    if self.fts_enabled:
                        connection.execute("DELETE FROM file_index_fts WHERE path = ?", (row["path"],))

        return {
            "indexed": indexed,
            "skipped": skipped,
            "roots": [str(root) for root in scan_roots],
            "fts": self.fts_enabled,
        }

    def _fts_query(self, query):
        tokens = re.findall(r"[\w-]+", query, flags=re.UNICODE)
        return " OR ".join(f'"{token}"*' for token in tokens[:12])

    def search(self, query, limit=10):
        query = str(query or "").strip()
        if not query:
            return []

        limit = max(1, min(50, int(limit)))
        with self._connect() as connection:
            rows = []
            if self.fts_enabled:
                fts_query = self._fts_query(query)
                if fts_query:
                    try:
                        rows = connection.execute(
                            """
                            SELECT f.path, f.name, f.extension, f.size_bytes,
                                   f.modified_at, bm25(file_index_fts) AS rank
                            FROM file_index_fts
                            JOIN file_index f ON f.path = file_index_fts.path
                            WHERE file_index_fts MATCH ?
                            ORDER BY rank ASC
                            LIMIT ?
                            """,
                            (fts_query, limit),
                        ).fetchall()
                    except sqlite3.OperationalError:
                        rows = []

            if not rows:
                pattern = f"%{query}%"
                rows = connection.execute(
                    """
                    SELECT path, name, extension, size_bytes, modified_at,
                           0 AS rank
                    FROM file_index
                    WHERE name LIKE ? OR path LIKE ? OR content LIKE ?
                    ORDER BY modified_at DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, pattern, limit),
                ).fetchall()

        return [dict(row) for row in rows]

    def stats(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS files, COALESCE(SUM(size_bytes), 0) AS bytes FROM file_index"
            ).fetchone()
        return {
            "files": int(row["files"]),
            "bytes": int(row["bytes"]),
            "roots": [str(root) for root in self.roots],
            "fts": self.fts_enabled,
        }
