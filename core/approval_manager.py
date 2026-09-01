import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class ApprovalManager:
    """Persists approval requests for sensitive JARVIS tool actions."""

    def __init__(self, db_path=None):
        project_root = Path(__file__).resolve().parents[1]
        configured_path = os.getenv("JARVIS_DB_PATH")
        self.db_path = Path(db_path or configured_path or project_root / "data" / "jarvis.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    permission_level INTEGER NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    result TEXT
                )
                """
            )

    def create(self, action, arguments, permission_level, reason=None):
        approval_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_requests (
                    approval_id, action, arguments_json, permission_level,
                    reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    approval_id,
                    action,
                    json.dumps(arguments or {}, ensure_ascii=False, default=str),
                    int(permission_level),
                    reason,
                    utc_now_iso(),
                ),
            )
        return self.get(approval_id)

    def get(self, approval_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM approval_requests WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        return self._deserialize(row) if row else None

    def find(self, reference):
        reference = str(reference or "").strip()
        if not reference:
            return None

        exact = self.get(reference)
        if exact:
            return exact

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM approval_requests
                WHERE approval_id LIKE ?
                ORDER BY created_at DESC
                LIMIT 2
                """,
                (reference + "%",),
            ).fetchall()
        if len(rows) != 1:
            return None
        return self._deserialize(rows[0])

    def list(self, status="pending", limit=20):
        query = "SELECT * FROM approval_requests"
        parameters = []
        if status:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(max(1, min(100, int(limit))))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._deserialize(row) for row in rows]

    def resolve(self, approval_id, status, result=None):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE approval_requests
                SET status = ?, resolved_at = ?, result = ?
                WHERE approval_id = ?
                """,
                (status, utc_now_iso(), None if result is None else str(result), approval_id),
            )
        return self.get(approval_id)

    def _deserialize(self, row):
        item = dict(row)
        try:
            item["arguments"] = json.loads(item.pop("arguments_json"))
        except (TypeError, json.JSONDecodeError):
            item["arguments"] = {}
            item.pop("arguments_json", None)
        return item
