from core.event_bus import EventBus
from core.intent_engine import IntentEngine
from core.task import TaskStatus
from models.model_router import ModelRouter
from tasks.background_runtime import BackgroundTaskRuntime
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore
from tasks.verifier import BasicVerifier
from tools.tool_registry import ToolRegistry


class Orchestrator:
    """Coordinates intent, routing, tools, persistence, and task execution."""

    def __init__(
        self,
        intent_engine=None,
        model_router=None,
        tool_registry=None,
        event_bus=None,
        task_store=None,
        task_manager=None,
        verifier=None,
        runtime=None,
    ):
        self.intent_engine = intent_engine or IntentEngine()
        self.model_router = model_router or ModelRouter()
        self.tools = tool_registry or ToolRegistry()
        self.event_bus = event_bus or EventBus()
        self.task_store = task_store or TaskStore()
        self.task_manager = task_manager or TaskManager(
            store=self.task_store,
            event_bus=self.event_bus,
        )
        self.verifier = verifier or BasicVerifier()
        self.runtime = runtime or BackgroundTaskRuntime(
            task_manager=self.task_manager,
            verifier=self.verifier,
        )

    def handle(self, user_input, context=None):
        task = self.intent_engine.analyze(user_input)
        self.task_manager.register(task)

        if task.background:
            self.runtime.submit(
                task,
                lambda current_task: self._execute(current_task, context=context),
            )
            return (
                f"Started background task {task.task_id[:8]} "
                f"for {task.intent}. You can continue working."
            )

        try:
            self.task_manager.transition(task, TaskStatus.RUNNING)
            result = self._execute(task, context=context)
            self.task_manager.transition(task, TaskStatus.VERIFYING)

            verification = self.verifier.verify(task, result)
            if not verification.passed:
                raise RuntimeError(
                    f"Verification failed: {verification.reason}"
                )

            self.task_manager.complete(task, result=result)
            return result
        except Exception as error:
            self.task_manager.fail(task, error)
            return f"JARVIS task failed: {error}"

    def _execute(self, task, context=None):
        return self.model_router.generate(
            task=task,
            context=context,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute,
        )

    def get_task(self, task_reference):
        return self.task_manager.find(task_reference)

    def list_tasks(self, limit=20, status=None):
        return self.task_manager.list(limit=limit, status=status)

    def shutdown(self):
        self.runtime.shutdown(wait=False)
