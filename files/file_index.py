import json
import math
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from files.embedding_provider import EmbeddingError, OllamaEmbeddingProvider


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class FileIndex:
    """SQLite-backed local file index with lexical + optional semantic search.

    Lexical search is always available. Semantic search is opt-in and uses a
    local Ollama embedding model, keeping private file retrieval local by
    default. The implementation uses SQLite plus cosine similarity so JARVIS
    does not need a vector database during early development.
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

    def __init__(
        self,
        db_path=None,
        roots=None,
        max_text_bytes=None,
        embedding_provider=None,
    ):
        project_root = Path(__file__).resolve().parents[1]
        configured_db = os.getenv("JARVIS_DB_PATH")
        self.db_path = Path(
            db_path or configured_db or project_root / "data" / "jarvis.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_text_bytes = int(
            max_text_bytes
            or os.getenv("JARVIS_FILE_MAX_TEXT_BYTES", 1_000_000)
        )
        self.embed_text_chars = max(
            256,
            int(os.getenv("JARVIS_EMBED_TEXT_CHARS", "6000")),
        )
        self.embedding_batch_size = max(
            1,
            int(os.getenv("JARVIS_EMBED_BATCH_SIZE", "24")),
        )
        self.embedding_provider = (
            embedding_provider
            if embedding_provider is not None
            else OllamaEmbeddingProvider()
        )
        self.roots = self._resolve_roots(roots, project_root)
        self.fts_enabled = False
        self._initialize()

    def _resolve_roots(self, roots, project_root):
        if roots:
            candidates = roots
        else:
            configured = os.getenv("JARVIS_INDEX_PATHS", "").strip()
            candidates = (
                [item for item in configured.split(os.pathsep) if item]
                if configured
                else [project_root]
            )

        resolved = []
        for item in candidates:
            try:
                path = Path(item).expanduser().resolve()
            except OSError:
                continue
            if path.exists() and path not in resolved:
                resolved.append(path)
        return resolved

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _ensure_column(connection, table, column, definition):
        columns = {
            row[1]
            for row in connection.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }
        if column not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

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
                    indexed_at TEXT NOT NULL,
                    embedding_json TEXT,
                    embedding_model TEXT
                )
                """
            )
            self._ensure_column(
                connection,
                "file_index",
                "embedding_json",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "file_index",
                "embedding_model",
                "TEXT",
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

    def _semantic_text(self, path, content):
        header = f"File name: {path.name}\nPath: {path}\n"
        if content:
            return header + content[: self.embed_text_chars]
        return header

    def _upsert(self, connection, path):
        stat = path.stat()
        content = self._read_content(path, stat.st_size)
        path_text = str(path)

        existing = connection.execute(
            """
            SELECT modified_at, embedding_json, embedding_model
            FROM file_index WHERE path = ?
            """,
            (path_text,),
        ).fetchone()

        provider_model = getattr(self.embedding_provider, "model", None)
        needs_embedding = bool(
            getattr(self.embedding_provider, "is_available", False)
            and (
                existing is None
                or float(existing["modified_at"]) != float(stat.st_mtime)
                or not existing["embedding_json"]
                or existing["embedding_model"] != provider_model
            )
        )

        connection.execute(
            """
            INSERT INTO file_index (
                path, name, extension, size_bytes, modified_at, content,
                indexed_at, embedding_json, embedding_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                extension = excluded.extension,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                content = excluded.content,
                indexed_at = excluded.indexed_at,
                embedding_json = CASE
                    WHEN file_index.modified_at = excluded.modified_at
                    THEN file_index.embedding_json ELSE NULL END,
                embedding_model = CASE
                    WHEN file_index.modified_at = excluded.modified_at
                    THEN file_index.embedding_model ELSE NULL END
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
            connection.execute(
                "DELETE FROM file_index_fts WHERE path = ?",
                (path_text,),
            )
            connection.execute(
                "INSERT INTO file_index_fts (path, name, content) VALUES (?, ?, ?)",
                (path_text, path.name, content or ""),
            )

        if needs_embedding:
            return path_text, self._semantic_text(path, content)
        return None

    def _embed_pending(self, pending):
        if not pending or not getattr(
            self.embedding_provider,
            "is_available",
            False,
        ):
            return 0, None

        model = getattr(self.embedding_provider, "model", None)
        embedded = 0

        try:
            for start in range(0, len(pending), self.embedding_batch_size):
                batch = pending[start : start + self.embedding_batch_size]
                texts = [item[1] for item in batch]
                vectors = self.embedding_provider.embed(texts)

                if len(vectors) != len(batch):
                    raise EmbeddingError(
                        "Embedding provider returned a mismatched vector count."
                    )

                with self._connect() as connection:
                    for (path_text, _), vector in zip(batch, vectors):
                        connection.execute(
                            """
                            UPDATE file_index
                            SET embedding_json = ?, embedding_model = ?
                            WHERE path = ?
                            """,
                            (
                                json.dumps(vector, separators=(",", ":")),
                                model,
                                path_text,
                            ),
                        )
                        embedded += 1
        except Exception as error:
            return embedded, str(error)

        return embedded, None

    def scan(self, roots=None):
        scan_roots = (
            self._resolve_roots(
                roots,
                Path(__file__).resolve().parents[1],
            )
            if roots
            else self.roots
        )
        indexed = 0
        skipped = 0
        discovered = set()
        embedding_pending = []

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
                        if any(
                            part.startswith(".")
                            for part in path.relative_to(root).parts
                        ):
                            continue

                        pending = self._upsert(connection, path)
                        if pending:
                            embedding_pending.append(pending)
                        discovered.add(str(path))
                        indexed += 1
                    except (OSError, ValueError):
                        skipped += 1

            rows = connection.execute(
                "SELECT path FROM file_index"
            ).fetchall()
            for row in rows:
                candidate = Path(row["path"])
                in_scope = any(
                    candidate == root or root in candidate.parents
                    for root in scan_roots
                )
                if in_scope and row["path"] not in discovered:
                    connection.execute(
                        "DELETE FROM file_index WHERE path = ?",
                        (row["path"],),
                    )
                    if self.fts_enabled:
                        connection.execute(
                            "DELETE FROM file_index_fts WHERE path = ?",
                            (row["path"],),
                        )

        embedded, semantic_error = self._embed_pending(embedding_pending)

        return {
            "indexed": indexed,
            "skipped": skipped,
            "roots": [str(root) for root in scan_roots],
            "fts": self.fts_enabled,
            "semantic": bool(
                getattr(self.embedding_provider, "is_available", False)
            ),
            "embedded": embedded,
            "semantic_error": semantic_error,
        }

    def _fts_query(self, query):
        tokens = re.findall(r"[\w-]+", query, flags=re.UNICODE)
        return " OR ".join(f'"{token}"*' for token in tokens[:12])

    def _lexical_search(self, connection, query, limit):
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

    @staticmethod
    def _cosine_similarity(a, b):
        if not a or not b or len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if not norm_a or not norm_b:
            return -1.0
        return dot / (norm_a * norm_b)

    def _semantic_search(self, query, limit):
        if not getattr(self.embedding_provider, "is_available", False):
            return []

        try:
            vectors = self.embedding_provider.embed([query])
            if not vectors:
                return []
            query_vector = vectors[0]
        except Exception:
            return []

        model = getattr(self.embedding_provider, "model", None)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT path, name, extension, size_bytes, modified_at,
                       embedding_json
                FROM file_index
                WHERE embedding_json IS NOT NULL
                  AND embedding_model = ?
                """,
                (model,),
            ).fetchall()

        ranked = []
        for row in rows:
            try:
                vector = json.loads(row["embedding_json"])
            except (TypeError, json.JSONDecodeError):
                continue

            score = self._cosine_similarity(query_vector, vector)
            item = dict(row)
            item.pop("embedding_json", None)
            item["semantic_score"] = score
            ranked.append(item)

        ranked.sort(
            key=lambda item: item["semantic_score"],
            reverse=True,
        )
        return ranked[:limit]

    @staticmethod
    def _fuse_results(lexical, semantic, limit):
        if not semantic:
            return lexical[:limit]
        if not lexical:
            return semantic[:limit]

        by_path = {}
        scores = {}

        for rank, item in enumerate(lexical, start=1):
            path = item["path"]
            by_path[path] = dict(item)
            scores[path] = scores.get(path, 0.0) + 1.0 / (60 + rank)

        for rank, item in enumerate(semantic, start=1):
            path = item["path"]
            if path not in by_path:
                by_path[path] = dict(item)
            else:
                by_path[path]["semantic_score"] = item.get("semantic_score")
            scores[path] = scores.get(path, 0.0) + 1.0 / (60 + rank)

        combined = []
        for path, item in by_path.items():
            item["fusion_score"] = scores[path]
            combined.append(item)

        combined.sort(
            key=lambda item: item["fusion_score"],
            reverse=True,
        )
        return combined[:limit]

    def search(self, query, limit=10):
        query = str(query or "").strip()
        if not query:
            return []

        limit = max(1, min(50, int(limit)))
        candidate_limit = min(100, max(limit * 3, limit))

        with self._connect() as connection:
            lexical = self._lexical_search(
                connection,
                query,
                candidate_limit,
            )

        semantic = self._semantic_search(query, candidate_limit)
        return self._fuse_results(lexical, semantic, limit)

    def stats(self):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS files,
                       COALESCE(SUM(size_bytes), 0) AS bytes,
                       SUM(CASE WHEN embedding_json IS NOT NULL THEN 1 ELSE 0 END)
                           AS embedded_files
                FROM file_index
                """
            ).fetchone()
        return {
            "files": int(row["files"]),
            "bytes": int(row["bytes"]),
            "roots": [str(root) for root in self.roots],
            "fts": self.fts_enabled,
            "semantic": bool(
                getattr(self.embedding_provider, "is_available", False)
            ),
            "embedding_model": getattr(
                self.embedding_provider,
                "model",
                None,
            ),
            "embedded_files": int(row["embedded_files"] or 0),
        }
