import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class WorkspaceStore:
    """Persistent project/work-session state for JARVIS continuity."""

    def __init__(self, db_path=None):
        project_root = Path(__file__).resolve().parents[1]
        configured = os.getenv("JARVIS_DB_PATH")
        self.db_path = Path(db_path or configured or project_root / "data" / "jarvis.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

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

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    repo_url TEXT,
                    preferred_app TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_opened_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workspace_sessions (
                    session_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id)
                );
                """
            )

    def upsert_workspace(self, name, root_path, repo_url=None, preferred_app="vscode"):
        resolved = str(Path(root_path).expanduser().resolve())
        now = utc_now_iso()

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT workspace_id FROM workspaces WHERE root_path = ?",
                (resolved,),
            ).fetchone()

            workspace_id = existing["workspace_id"] if existing else str(uuid4())
            connection.execute(
                """
                INSERT INTO workspaces (
                    workspace_id, name, root_path, repo_url, preferred_app,
                    status, created_at, updated_at, last_opened_at
                ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
                ON CONFLICT(root_path) DO UPDATE SET
                    name=excluded.name,
                    repo_url=COALESCE(excluded.repo_url, workspaces.repo_url),
                    preferred_app=COALESCE(excluded.preferred_app, workspaces.preferred_app),
                    status='active',
                    updated_at=excluded.updated_at,
                    last_opened_at=excluded.last_opened_at
                """,
                (
                    workspace_id,
                    str(name).strip(),
                    resolved,
                    repo_url,
                    preferred_app,
                    now,
                    now,
                    now,
                ),
            )

        return self.get_workspace(workspace_id)

    def get_workspace(self, workspace_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
        return dict(row) if row else None

    def find_workspace(self, reference):
        reference = str(reference or "").strip()
        if not reference:
            return self.latest_workspace()

        with self._connect() as connection:
            exact = connection.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ? OR lower(name) = lower(?) LIMIT 1",
                (reference, reference),
            ).fetchone()
            if exact:
                return dict(exact)

            rows = connection.execute(
                """
                SELECT * FROM workspaces
                WHERE lower(name) LIKE lower(?) OR workspace_id LIKE ?
                ORDER BY COALESCE(last_opened_at, updated_at) DESC
                LIMIT 2
                """,
                (f"%{reference}%", f"{reference}%"),
            ).fetchall()

        if len(rows) == 1:
            return dict(rows[0])
        return None

    def list_workspaces(self, limit=20):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspaces
                WHERE status = 'active'
                ORDER BY COALESCE(last_opened_at, updated_at) DESC
                LIMIT ?
                """,
                (max(1, min(100, int(limit))),),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_workspace(self):
        items = self.list_workspaces(limit=1)
        return items[0] if items else None

    def touch_workspace(self, workspace_id):
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                "UPDATE workspaces SET last_opened_at = ?, updated_at = ? WHERE workspace_id = ?",
                (now, now, workspace_id),
            )
        return self.get_workspace(workspace_id)

    def save_session(self, workspace_id, state, summary=None):
        session_id = str(uuid4())
        created_at = utc_now_iso()
        payload = json.dumps(state or {}, ensure_ascii=False, default=str)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspace_sessions (
                    session_id, workspace_id, state_json, summary, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, workspace_id, payload, summary, created_at),
            )
            connection.execute(
                "UPDATE workspaces SET updated_at = ?, last_opened_at = ? WHERE workspace_id = ?",
                (created_at, created_at, workspace_id),
            )

        return self.latest_session(workspace_id)

    def latest_session(self, workspace_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM workspace_sessions
                WHERE workspace_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (workspace_id,),
            ).fetchone()

        if row is None:
            return None
        item = dict(row)
        try:
            item["state"] = json.loads(item.pop("state_json"))
        except (TypeError, json.JSONDecodeError):
            item["state"] = {}
            item.pop("state_json", None)
        return item
