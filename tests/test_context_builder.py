import tempfile
import unittest
from pathlib import Path

from core.context_builder import ContextBuilder
from core.task import Task
from memory.memory_manager import MemoryManager


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


if __name__ == "__main__":
    unittest.main()
