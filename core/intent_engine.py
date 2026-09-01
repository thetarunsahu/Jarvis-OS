from core.task import Task


class IntentEngine:
    """Lightweight deterministic first-pass intent classifier.

    The classifier deliberately stays cheap and predictable. Model-assisted
    intent analysis can be layered on later without changing the Task contract.
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

        if any(
            word in text
            for word in [
                "remind",
                "reminder",
                "schedule",
                "deadline",
                "goal",
                "plan my day",
                "daily plan",
                "daily brief",
            ]
        ):
            intent = "productivity"
            requires_tools = True
            complexity = 2

        if any(word in text for word in ["research", "compare", "find latest", "deep research"]):
            intent = "research"
            requires_tools = True
            complexity = 4
            background = True

        if any(word in text for word in ["code", "bug", "error", "fix", "refactor", "repository", "repo"]):
            intent = "coding"
            requires_tools = True
            complexity = 4
            background = True

        if any(word in text for word in ["ui", "ux", "frontend", "design", "redesign"]):
            intent = "ui_design"
            requires_tools = True
            complexity = 4
            background = True

        return Task(
            raw_input=user_input,
            intent=intent,
            complexity=complexity,
            requires_tools=requires_tools,
            background=background,
        )
