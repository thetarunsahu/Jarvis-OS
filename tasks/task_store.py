import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.task import Task, TaskStatus


class TaskStore:
    """SQLite persistence for task state and history."""

    def __init__(self, db_path=None):
        project_root = Path(__file__).resolve().parents[1]
        configured_path = os.getenv("JARVIS_DB_PATH")
        default_path = project_root / "data" / "jarvis.db"

        self.db_path = Path(db_path or configured_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    raw_input TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    complexity INTEGER NOT NULL,
                    requires_tools INTEGER NOT NULL,
                    background INTEGER NOT NULL,
                    preferred_provider TEXT,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result TEXT,
                    error TEXT
                )
                """
            )

    def save(self, task):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    task_id, raw_input, intent, complexity, requires_tools,
                    background, preferred_provider, metadata, status,
                    created_at, updated_at, result, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    raw_input=excluded.raw_input,
                    intent=excluded.intent,
                    complexity=excluded.complexity,
                    requires_tools=excluded.requires_tools,
                    background=excluded.background,
                    preferred_provider=excluded.preferred_provider,
                    metadata=excluded.metadata,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    result=excluded.result,
                    error=excluded.error
                """,
                (
                    task.task_id,
                    task.raw_input,
                    task.intent,
                    task.complexity,
                    int(task.requires_tools),
                    int(task.background),
                    task.preferred_provider,
                    json.dumps(task.metadata, ensure_ascii=False),
                    task.status.value,
                    task.created_at,
                    task.updated_at,
                    task.result,
                    task.error,
                ),
            )

    def get(self, task_id):
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        return self._row_to_task(row) if row else None

    def list(self, limit=50, status=None):
        query = "SELECT * FROM tasks"
        parameters = []

        if status is not None:
            status_value = TaskStatus(status).value
            query += " WHERE status = ?"
            parameters.append(status_value)

        query += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(int(limit))

        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, parameters).fetchall()

        return [self._row_to_task(row) for row in rows]

    @staticmethod
    def _row_to_task(row):
        return Task(
            raw_input=row["raw_input"],
            intent=row["intent"],
            complexity=row["complexity"],
            requires_tools=bool(row["requires_tools"]),
            background=bool(row["background"]),
            preferred_provider=row["preferred_provider"],
            metadata=json.loads(row["metadata"] or "{}"),
            task_id=row["task_id"],
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            result=row["result"],
            error=row["error"],
        )
