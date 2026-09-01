from core.orchestrator import Orchestrator


class Brain:
    """JARVIS intelligence entry point.

    Brain is intentionally thin. Orchestrator owns task analysis, routing,
    persistence, background execution, and model/tool coordination.
    """

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator or Orchestrator()

    def respond(self, user_input, context=None):
        return self.orchestrator.handle(user_input, context=context)

    def get_task(self, task_id):
        return self.orchestrator.get_task(task_id)

    def list_tasks(self, limit=20, status=None):
        return self.orchestrator.list_tasks(limit=limit, status=status)

    def shutdown(self):
        self.orchestrator.shutdown()
