from agents.agent_registry import AgentRegistry
from agents.agent_router import AgentRouter
from core.context_builder import ContextBuilder
from core.event_bus import EventBus
from core.intent_engine import IntentEngine
from core.task import TaskStatus
from models.model_router import ModelRouter
from observability.audit_log import AuditLogger
from productivity.reminder_scheduler import ReminderScheduler
from tasks.background_runtime import BackgroundTaskRuntime
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore
from tasks.verifier import BasicVerifier
from tools.tool_registry import ToolRegistry


class Orchestrator:
    """Coordinates intent, context, agents, models, tools, and execution."""

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
        agent_registry=None,
        agent_router=None,
        context_builder=None,
        audit_logger=None,
        reminder_scheduler=None,
    ):
        self.intent_engine = intent_engine or IntentEngine()
        self.model_router = model_router or ModelRouter()
        self.tools = tool_registry or ToolRegistry()
        self.event_bus = event_bus or EventBus()
        self.audit_logger = audit_logger or AuditLogger(self.event_bus)
        self.task_store = task_store or TaskStore()
        self.task_manager = task_manager or TaskManager(
            store=self.task_store,
            event_bus=self.event_bus,
        )
        self.verifier = verifier or BasicVerifier()
        self.context_builder = context_builder or ContextBuilder()
        self.agent_registry = agent_registry or AgentRegistry(
            model_router=self.model_router,
            tool_registry=self.tools,
        )
        self.agent_router = agent_router or AgentRouter(self.agent_registry)
        self.runtime = runtime or BackgroundTaskRuntime(
            task_manager=self.task_manager,
            verifier=self.verifier,
        )

        if reminder_scheduler is not None:
            self.reminder_scheduler = reminder_scheduler
        elif hasattr(self.tools, "productivity"):
            self.reminder_scheduler = ReminderScheduler(
                store=self.tools.productivity.store,
                event_bus=self.event_bus,
            )
        else:
            self.reminder_scheduler = None

        if self.reminder_scheduler is not None:
            self.reminder_scheduler.start()

    def handle(self, user_input, context=None):
        task = self.intent_engine.analyze(user_input)
        self.task_manager.register(task)

        if task.background:
            self.runtime.submit(
                task,
                lambda current_task: self._execute(
                    current_task,
                    explicit_context=context,
                ),
            )
            return (
                f"Started background task {task.task_id[:8]} "
                f"for {task.intent}. You can continue working."
            )

        try:
            self.task_manager.transition(task, TaskStatus.RUNNING)
            result = self._execute(task, explicit_context=context)
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

    def _execute(self, task, explicit_context=None):
        agent = self.agent_router.route(task)
        task.metadata["agent"] = agent.name
        self.task_store.save(task)
        self.event_bus.publish(
            "agent.selected",
            task_id=task.task_id,
            agent=agent.name,
        )

        context = self.context_builder.build(
            task,
            explicit_context=explicit_context,
        )
        return agent.execute(task, context=context)

    def get_task(self, task_reference):
        return self.task_manager.find(task_reference)

    def list_tasks(self, limit=20, status=None):
        return self.task_manager.list(limit=limit, status=status)

    def list_approvals(self, limit=20):
        return self.tools.list_pending_approvals(limit=limit)

    def resolve_approval(self, reference, approved):
        result = self.tools.resolve_approval(reference, approved=approved)
        self.event_bus.publish(
            "approval.resolved",
            reference=reference,
            approved=bool(approved),
            result=str(result),
        )
        return result

    def shutdown(self):
        if self.reminder_scheduler is not None:
            self.reminder_scheduler.stop(wait=False)
        self.runtime.shutdown(wait=False)
