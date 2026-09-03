from files.file_index import FileIndex
from memory.memory_manager import MemoryManager
from productivity.productivity_store import ProductivityStore


class ContextBuilder:
    """Build the minimum useful context for a task.

    Context retrieval stays task-aware: file tasks can receive ranked local
    file matches, productivity tasks can receive active goals/reminders, and
    ordinary conversation avoids loading unrelated personal state.
    """

    def __init__(
        self,
        memory_manager=None,
        file_index=None,
        productivity_store=None,
    ):
        self.memory = memory_manager or MemoryManager()
        self.file_index = file_index
        self.productivity_store = productivity_store

    def _get_file_index(self):
        if self.file_index is None:
            try:
                self.file_index = FileIndex()
            except Exception:
                self.file_index = False
        return self.file_index if self.file_index is not False else None

    def _get_productivity_store(self):
        if self.productivity_store is None:
            try:
                self.productivity_store = ProductivityStore()
            except Exception:
                self.productivity_store = False
        return self.productivity_store if self.productivity_store is not False else None

    def build(self, task, explicit_context=None):
        sections = []

        if explicit_context:
            sections.append(f"Explicit context:\n{explicit_context}")

        memories = self.memory.snapshot()
        if memories:
            memory_lines = "\n".join(
                f"- {key}: {value}"
                for key, value in memories.items()
            )
            sections.append(f"Known user memory:\n{memory_lines}")

        if task.intent == "file":
            index = self._get_file_index()
            if index is not None:
                try:
                    matches = index.search(task.raw_input, limit=5)
                except Exception:
                    matches = []
                if matches:
                    file_lines = "\n".join(
                        f"- {match['name']} | {match['path']}"
                        for match in matches
                    )
                    sections.append(
                        "Relevant indexed local files (ranked candidates):\n"
                        + file_lines
                    )

        if task.intent == "productivity":
            store = self._get_productivity_store()
            if store is not None:
                try:
                    goals = store.list_goals(status="active", limit=8)
                    reminders = store.list_reminders(status="pending", limit=8)
                except Exception:
                    goals = []
                    reminders = []

                if goals:
                    goal_lines = "\n".join(
                        f"- {goal['title']} | progress={goal['progress']}% | "
                        f"target={goal.get('target_date') or 'unset'}"
                        for goal in goals
                    )
                    sections.append("Active goals:\n" + goal_lines)

                if reminders:
                    reminder_lines = "\n".join(
                        f"- {reminder['text']} | due={reminder['due_at']}"
                        for reminder in reminders
                    )
                    sections.append("Pending reminders:\n" + reminder_lines)

        if task.metadata:
            metadata_lines = "\n".join(
                f"- {key}: {value}"
                for key, value in task.metadata.items()
            )
            sections.append(f"Task metadata:\n{metadata_lines}")

        return "\n\n".join(sections) if sections else None
