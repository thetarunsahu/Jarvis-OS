from core.context_builder import ContextBuilder
from core.orchestrator import Orchestrator


class Brain:
    """JARVIS intelligence entry point.

    Brain stays intentionally thin. Orchestrator owns task analysis, routing,
    persistence, background execution, context, and model/tool coordination.
    """

    def __init__(self, orchestrator=None, memory_manager=None):
        if orchestrator is not None:
            self.orchestrator = orchestrator
        else:
            context_builder = ContextBuilder(memory_manager=memory_manager)
            self.orchestrator = Orchestrator(context_builder=context_builder)

    def respond(self, user_input, context=None):
        return self.orchestrator.handle(user_input, context=context)

    def get_task(self, task_id):
        return self.orchestrator.get_task(task_id)

    def list_tasks(self, limit=20, status=None):
        return self.orchestrator.list_tasks(limit=limit, status=status)

    def shutdown(self):
        self.orchestrator.shutdown()
