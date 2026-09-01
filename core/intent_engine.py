from core.task import Task


class IntentEngine:
    """Lightweight first-pass intent classifier.

    This intentionally starts deterministic. More advanced model-assisted
    intent analysis can be added later without changing the Task contract.
    """

    def analyze(self, user_input):
        text = user_input.lower().strip()

        intent = "conversation"
        complexity = 1
        requires_tools = False
        background = False

        if any(word in text for word in ["file", "folder", "document", "pdf", "image"]):
            intent = "file"
            requires_tools = True
            complexity = 2

        if any(word in text for word in ["system info", "cpu", "ram", "processor", "battery"]):
            intent = "system"
            requires_tools = True
            complexity = 1

        if any(word in text for word in ["remind", "reminder", "schedule", "deadline"]):
            intent = "productivity"
            complexity = 2

        if any(word in text for word in ["research", "compare", "find latest", "deep research"]):
            intent = "research"
            complexity = 4
            background = True

        if any(word in text for word in ["code", "bug", "error", "fix", "refactor", "repository", "repo"]):
            intent = "coding"
            complexity = 4
            background = True

        if any(word in text for word in ["ui", "ux", "frontend", "design", "redesign"]):
            intent = "ui_design"
            complexity = 4
            background = True

        return Task(
            raw_input=user_input,
            intent=intent,
            complexity=complexity,
            requires_tools=requires_tools,
            background=background,
        )
