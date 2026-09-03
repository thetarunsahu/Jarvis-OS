import json
from pathlib import Path
from threading import RLock


class MemoryManager:
    """Small persistent key-value memory used by the current JARVIS core.

    This remains intentionally simple until semantic/project memory is added.
    The public contract is thread-safe so background workers can safely read
    and update it.
    """

    def __init__(self, memory_file=None):
        self.memory_file = Path(
            memory_file or Path(__file__).parent / "data" / "memory.json"
        )
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._load_memory()

    def _load_memory(self):
        with self._lock:
            try:
                with open(self.memory_file, "r", encoding="utf-8") as file:
                    self.memory = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                self.memory = {}

    def _save_memory(self):
        with self._lock:
            with open(self.memory_file, "w", encoding="utf-8") as file:
                json.dump(
                    self.memory,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )

    def remember(self, key, value):
        with self._lock:
            self.memory[key] = value
            self._save_memory()
        return f"I'll remember that {key} is {value}."

    def recall(self, key):
        with self._lock:
            return self.memory.get(
                key,
                "I don't remember that yet.",
            )

    def snapshot(self):
        with self._lock:
            return dict(self.memory)

    def get_all(self):
        memories = self.snapshot()
        if not memories:
            return "I don't have any memories yet."

        return "\n".join(
            f"- {key}: {value}"
            for key, value in memories.items()
        )

    def forget(self, key):
        with self._lock:
            if key not in self.memory:
                return "I don't have that memory."

            del self.memory[key]
            self._save_memory()

        return f"I've forgotten {key}."
