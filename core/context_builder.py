from memory.memory_manager import MemoryManager


class ContextBuilder:
    """Builds the minimum useful context for a task.

    The current implementation uses explicit context plus key-value memory.
    Later this layer can add project memory, semantic retrieval, recent task
    history, active files, calendar state, and user goals without changing
    agents or model providers.
    """

    def __init__(self, memory_manager=None):
        self.memory = memory_manager or MemoryManager()

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

        if task.metadata:
            metadata_lines = "\n".join(
                f"- {key}: {value}"
                for key, value in task.metadata.items()
            )
            sections.append(f"Task metadata:\n{metadata_lines}")

        return "\n\n".join(sections) if sections else None
