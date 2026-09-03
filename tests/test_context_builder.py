import tempfile
import unittest
from pathlib import Path

from core.context_builder import ContextBuilder
from core.task import Task
from memory.memory_manager import MemoryManager


class FakeFileIndex:
    def search(self, query, limit=5):
        return [
            {
                "name": "agribot_final.png",
                "path": "D:/Projects/Agribot/agribot_final.png",
            }
        ]


class FakeProductivityStore:
    def list_goals(self, status="active", limit=8):
        return [
            {
                "title": "Become internship ready",
                "progress": 35,
                "target_date": "2027-03-01",
            }
        ]

    def list_reminders(self, status="pending", limit=8):
        return [
            {
                "text": "Solve DSA problems",
                "due_at": "2026-09-03T20:00:00+05:30",
            }
        ]


class ContextBuilderTests(unittest.TestCase):
    def test_memory_and_explicit_context_are_combined(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(
                memory_file=Path(temp_dir) / "memory.json"
            )
            memory.remember("primary_goal", "be internship ready")

            builder = ContextBuilder(memory_manager=memory)
            task = Task(raw_input="plan my day")
            task.metadata["agent"] = "productivity"

            context = builder.build(
                task,
                explicit_context="DSA target: 3 problems",
            )

            self.assertIn("DSA target: 3 problems", context)
            self.assertIn("primary_goal: be internship ready", context)
            self.assertIn("agent: productivity", context)

    def test_file_task_receives_ranked_file_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(memory_file=Path(temp_dir) / "memory.json")
            builder = ContextBuilder(
                memory_manager=memory,
                file_index=FakeFileIndex(),
            )
            task = Task(
                raw_input="find the agribot image I showed my mentor",
                intent="file",
            )

            context = builder.build(task)

            self.assertIn("agribot_final.png", context)
            self.assertIn("ranked candidates", context)

    def test_productivity_task_receives_goals_and_reminders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(memory_file=Path(temp_dir) / "memory.json")
            builder = ContextBuilder(
                memory_manager=memory,
                productivity_store=FakeProductivityStore(),
            )
            task = Task(raw_input="plan my day", intent="productivity")

            context = builder.build(task)

            self.assertIn("Become internship ready", context)
            self.assertIn("Solve DSA problems", context)


if __name__ == "__main__":
    unittest.main()
