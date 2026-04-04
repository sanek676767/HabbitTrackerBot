from abc import ABC, abstractmethod
from typing import Any

from app.workers.celery_app import celery_app


class TaskQueue(ABC):
    @abstractmethod
    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError


class CeleryTaskQueue(TaskQueue):
    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        task_result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
        return task_result.id
