from concurrent.futures import ThreadPoolExecutor

from core.task import TaskStatus
from tasks.task_manager import TaskManager


class BackgroundTaskRuntime:
    """Runs long tasks without blocking the JARVIS conversation loop."""

    def __init__(self, task_manager=None, max_workers=3):
        self.task_manager = task_manager or TaskManager()
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="jarvis-worker",
        )
        self._futures = {}

    def submit(self, task, handler):
        if task.status == TaskStatus.CREATED:
            self.task_manager.transition(task, TaskStatus.QUEUED)

        future = self.executor.submit(self._run, task, handler)
        self._futures[task.task_id] = future
        return future

    def _run(self, task, handler):
        try:
            self.task_manager.transition(task, TaskStatus.RUNNING)
            result = handler(task)
            self.task_manager.complete(task, result=result)
            return result
        except Exception as error:
            self.task_manager.fail(task, error)
            raise

    def future(self, task_id):
        return self._futures.get(task_id)

    def is_running(self, task_id):
        future = self.future(task_id)
        return bool(future and not future.done())

    def shutdown(self, wait=True):
        self.executor.shutdown(wait=wait)
