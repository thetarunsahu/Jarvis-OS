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

        return self.model_router.generate(
            task=task,
            context=merged_context,
            tools=self.tools.get_tool_definitions(),
            executor=execute_tool,
        )
