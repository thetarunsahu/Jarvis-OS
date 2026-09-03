class ModelAgent:
    """Specialist agent backed by ModelRouter and the shared tool registry."""

    def __init__(
        self,
        name,
        intents,
        instructions,
        model_router,
        tool_registry,
    ):
        self.name = name
        self.intents = set(intents)
        self.instructions = instructions.strip()
        self.model_router = model_router
        self.tools = tool_registry

    def can_handle(self, task):
        return task.intent in self.intents

    def execute(self, task, context=None):
        merged_context = self.instructions
        if context:
            merged_context += f"\n\nRelevant task context:\n{context}"

        def execute_tool(tool_name, arguments=None):
            return self.tools.execute(
                tool_name,
                arguments=arguments,
                task_id=task.task_id,
            )

        # Ordinary conversation should behave like conversation. Passing the
        # complete desktop tool catalog to a small local model can make it
        # incorrectly believe every answer must come from a tool. Only expose
        # tools when deterministic intent analysis says the task needs them.
        needs_tools = bool(task.requires_tools)
        tool_definitions = self.tools.get_tool_definitions() if needs_tools else None
        executor = execute_tool if needs_tools else None

        return self.model_router.generate(
            task=task,
            context=merged_context,
            tools=tool_definitions,
            executor=executor,
        )
