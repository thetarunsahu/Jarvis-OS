import json
from pathlib import Path


class MemoryManager:

    def __init__(self):
        self.memory_file = (
            Path(__file__).parent / "data" / "memory.json"
        )

        self.memory_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._load_memory()

    def _load_memory(self):
        try:
            with open(self.memory_file, "r", encoding="utf-8") as file:
                self.memory = json.load(file)

        except (FileNotFoundError, json.JSONDecodeError):
            self.memory = {}

    def _save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as file:
            json.dump(
                self.memory,
                file,
                indent=4,
                ensure_ascii=False
            )

    def remember(self, key, value):
        self.memory[key] = value
        self._save_memory()

        return f"I'll remember that {key} is {value}."

    def recall(self, key):
        return self.memory.get(
            key,
            "I don't remember that yet."
        )

    def get_all(self):
        if not self.memory:
            return "I don't have any memories yet."

        memories = []

        for key, value in self.memory.items():
            memories.append(f"- {key}: {value}")

        return "\n".join(memories)

    def forget(self, key):
        if key not in self.memory:
            return "I don't have that memory."

        del self.memory[key]
        self._save_memory()

        return f"I've forgotten {key}."