from core.event_bus import EventBus
from core.task import TaskStatus
from tasks.task_store import TaskStore


class InvalidTaskTransition(RuntimeError):
    pass


class TaskManager:
    """Owns task lifecycle transitions, persistence, and task events."""

    _allowed_transitions = {
        TaskStatus.CREATED: {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
        },
        TaskStatus.QUEUED: {
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        },
        TaskStatus.RUNNING: {
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.VERIFYING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        },
        TaskStatus.WAITING_APPROVAL: {
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        },
        TaskStatus.VERIFYING: {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        },
        TaskStatus.COMPLETED: set(),
        TaskStatus.FAILED: set(),
        TaskStatus.CANCELLED: set(),
    }

    def __init__(self, store=None, event_bus=None):
        self.store = store or TaskStore()
        self.event_bus = event_bus or EventBus()

    def register(self, task):
        self.store.save(task)
        self.event_bus.publish(
            "task.created",
            task_id=task.task_id,
            intent=task.intent,
            background=task.background,
        )
        return task

    def transition(self, task, status):
        target = TaskStatus(status)

        if target == task.status:
            return task

        allowed = self._allowed_transitions.get(task.status, set())
        if target not in allowed:
            raise InvalidTaskTransition(
                f"Cannot move task {task.task_id} from "
                f"{task.status.value} to {target.value}."
            )

        previous = task.status
        task.set_status(target)
        self.store.save(task)
        self.event_bus.publish(
            "task.status_changed",
            task_id=task.task_id,
            previous_status=previous.value,
            status=target.value,
        )
        self.event_bus.publish(
            f"task.{target.value}",
            task_id=task.task_id,
        )
        return task

    def complete(self, task, result=None):
        if task.status == TaskStatus.RUNNING:
            self.transition(task, TaskStatus.VERIFYING)

        if task.status != TaskStatus.VERIFYING:
            raise InvalidTaskTransition(
                f"Task {task.task_id} must be verifying before completion."
            )

        task.complete(result)
        self.store.save(task)
        self.event_bus.publish(
            "task.completed",
            task_id=task.task_id,
            result=task.result,
        )
        return task

    def fail(self, task, error):
        if task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            return task

        task.fail(error)
        self.store.save(task)
        self.event_bus.publish(
            "task.failed",
            task_id=task.task_id,
            error=task.error,
        )
        return task

    def get(self, task_id):
        return self.store.get(task_id)

    def list(self, limit=50, status=None):
        return self.store.list(limit=limit, status=status)
