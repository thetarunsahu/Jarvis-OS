class AgentRouter:
    """Selects the smallest specialist agent capable of handling a task."""

    def __init__(self, registry):
        self.registry = registry

    def route(self, task):
        for agent in self.registry.all():
            if agent.can_handle(task):
                return agent

        return self.registry.get("general")
