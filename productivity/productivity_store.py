import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_datetime(value):
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("Datetime must include a timezone offset.")
    return parsed.astimezone(timezone.utc).isoformat()


class ProductivityStore:
    """SQLite storage for personal goals and reminders."""

    def __init__(self, db_path=None):
        project_root = Path(__file__).resolve().parents[1]
        configured_path = os.getenv("JARVIS_DB_PATH")
        default_path = project_root / "data" / "jarvis.db"
        self.db_path = Path(db_path or configured_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    target_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    notified_at TEXT,
                    completed_at TEXT
                );
                """
            )
            self._ensure_column(
                connection,
                table="reminders",
                column="notified_at",
                definition="TEXT",
            )

    @staticmethod
    def _ensure_column(connection, table, column, definition):
        columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    def create_goal(self, title, target_date=None):
        goal_id = str(uuid4())
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO goals (
                    goal_id, title, status, progress,
                    target_date, created_at, updated_at
                ) VALUES (?, ?, 'active', 0, ?, ?, ?)
                """,
                (goal_id, title.strip(), target_date, now, now),
            )
        return self.get_goal(goal_id)

    def get_goal(self, goal_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM goals WHERE goal_id = ?",
                (goal_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_goals(self, status="active", limit=20):
        query = "SELECT * FROM goals"
        parameters = []
        if status:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        parameters.append(int(limit))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def update_goal(self, goal_id, progress=None, status=None):
        goal = self.get_goal(goal_id)
        if goal is None:
            return None

        new_progress = goal["progress"] if progress is None else int(progress)
        new_progress = max(0, min(100, new_progress))
        new_status = status or goal["status"]
        if new_progress == 100 and status is None:
            new_status = "completed"

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE goals
                SET progress = ?, status = ?, updated_at = ?
                WHERE goal_id = ?
                """,
                (new_progress, new_status, utc_now_iso(), goal_id),
            )
        return self.get_goal(goal_id)

    def create_reminder(self, text, due_at):
        reminder_id = str(uuid4())
        normalized_due_at = normalize_datetime(due_at)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reminders (
                    reminder_id, text, due_at, status, created_at
                ) VALUES (?, ?, ?, 'pending', ?)
                """,
                (
                    reminder_id,
                    text.strip(),
                    normalized_due_at,
                    utc_now_iso(),
                ),
            )
        return self.get_reminder(reminder_id)

    def get_reminder(self, reminder_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE reminder_id = ?",
                (reminder_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_reminders(self, status="pending", limit=20):
        query = "SELECT * FROM reminders"
        parameters = []
        if status:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY due_at ASC LIMIT ?"
        parameters.append(int(limit))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def due_reminders(self, now_iso=None):
        normalized_now = (
            normalize_datetime(now_iso)
            if now_iso is not None
            else utc_now_iso()
        )
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM reminders
                WHERE status = 'pending' AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (normalized_now,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_reminder_notified(self, reminder_id):
        reminder = self.get_reminder(reminder_id)
        if reminder is None:
            return None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reminders
                SET status = 'notified', notified_at = ?
                WHERE reminder_id = ?
                """,
                (utc_now_iso(), reminder_id),
            )
        return self.get_reminder(reminder_id)

    def complete_reminder(self, reminder_id):
        reminder = self.get_reminder(reminder_id)
        if reminder is None:
            return None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reminders
                SET status = 'completed', completed_at = ?
                WHERE reminder_id = ?
                """,
                (utc_now_iso(), reminder_id),
            )
        return self.get_reminder(reminder_id)
