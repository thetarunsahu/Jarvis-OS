import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.approval_manager import ApprovalManager
from files.file_index import FileIndex
from productivity.productivity_store import ProductivityStore
from tasks.task_store import TaskStore


class DisabledEmbeddingProvider:
    is_available = False
    model = None


class SQLiteLifecycleTests(unittest.TestCase):
    def assert_connection_closes(self, store):
        with store._connect() as connection:
            connection.execute("SELECT 1")

        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_task_store_closes_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = TaskStore(Path(temp_dir) / "jarvis.db")
            self.assert_connection_closes(store)

    def test_productivity_store_closes_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProductivityStore(Path(temp_dir) / "jarvis.db")
            self.assert_connection_closes(store)

    def test_approval_manager_closes_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalManager(Path(temp_dir) / "jarvis.db")
            self.assert_connection_closes(store)

    def test_file_index_closes_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            store = FileIndex(
                db_path=Path(temp_dir) / "jarvis.db",
                roots=[root],
                embedding_provider=DisabledEmbeddingProvider(),
            )
            self.assert_connection_closes(store)


if __name__ == "__main__":
    unittest.main()
