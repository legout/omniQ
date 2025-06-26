import json
from typing import Any, AsyncGenerator, List, Optional

import fsspec
import msgspec

from omniq.models import Task, TaskEvent, TaskResult
from omniq.serialization import default_serializer
from omniq.storage import BaseEventStorage, BaseResultStorage, BaseTaskQueue


class FsspecTaskQueue(BaseTaskQueue):
    """
    A task queue using fsspec for storage. Best for simple, file-based workflows.
    Note: This implementation's locking is basic and may not be robust for
    high-concurrency, multi-node workers without a proper distributed lock manager.
    """

    def __init__(self, url: str, **storage_options: Any):
        protocol = url.split("://")[0]
        self.fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol, **storage_options)
        self.base_path = self.fs.unstrip_protocol(url)
        self.fs.mkdirs(self.base_path, exist_ok=True)

    async def enqueue(self, task: Task) -> str:
        if task.dependencies:
            raise NotImplementedError(
                "Task dependencies are not supported by the FsspecTaskQueue backend."
            )

        queue_path = self.fs.sep.join([self.base_path, task.queue])
        task_path = self.fs.sep.join([queue_path, task.id])
        self.fs.mkdirs(queue_path, exist_ok=True)
        serialized_task = default_serializer.serialize(task)
        async with self.fs.open_async(task_path, "wb") as f:
            await f.write(serialized_task)
        return task.id

    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        # Naive, non-atomic dequeue. A race condition can occur where two workers
        # list the same file. The atomic `mv` operation provides basic locking.
        for queue_name in queues:
            queue_path = self.fs.sep.join([self.base_path, queue_name])
            if not await self.fs._exists(queue_path):
                continue

            try:
                # This is not efficient for large queues.
                tasks = await self.fs._ls(queue_path, detail=False)
                if not tasks:
                    continue

                task_path = tasks[0]
                processing_path = f"{task_path}.processing"
                await self.fs._mv(task_path, processing_path)  # Atomic lock

                async with self.fs.open_async(processing_path, "rb") as f:
                    data = await f.read()

                task = default_serializer.deserialize(data, target_type=Task)
                # Hack to store the path for ack/nack
                setattr(task, "_processing_path", processing_path)
                return task
            except (FileNotFoundError, IndexError):
                continue  # Another worker got the task, or queue is empty.
        return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        # This requires searching all queues, which is inefficient.
        # A central task lookup directory would be a better design.
        raise NotImplementedError("get_task is not efficiently supported by FsspecTaskQueue")

    async def ack(self, task: Task) -> None:
        processing_path = getattr(task, "_processing_path", None)
        if processing_path and await self.fs._exists(processing_path):
            await self.fs._rm(processing_path)

    async def nack(self, task: Task, requeue: bool = True) -> None:
        processing_path = getattr(task, "_processing_path", None)
        if not (processing_path and await self.fs._exists(processing_path)):
            return

        if requeue:
            original_path = processing_path.removesuffix(".processing")
            await self.fs._mv(processing_path, original_path)
        else:
            # Move to a dead-letter queue
            dlq_path = self.fs.sep.join([self.base_path, "dead_letter"])
            self.fs.mkdirs(dlq_path, exist_ok=True)
            await self.fs._mv(processing_path, self.fs.sep.join([dlq_path, task.id]))


class FsspecResultStorage(BaseResultStorage):
    """Result storage using fsspec."""

    def __init__(self, url: str, **storage_options: Any):
        protocol = url.split("://")[0]
        self.fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol, **storage_options)
        self.base_path = self.fs.unstrip_protocol(url)
        self.fs.mkdirs(self.base_path, exist_ok=True)

    def _get_path(self, task_id: str) -> str:
        return self.fs.sep.join([self.base_path, task_id])

    async def store(self, result: TaskResult) -> None:
        path = self._get_path(result.task_id)
        serialized_result = default_serializer.serialize(result)
        async with self.fs.open_async(path, "wb") as f:
            await f.write(serialized_result)

    async def get(self, task_id: str) -> Optional[TaskResult]:
        path = self._get_path(task_id)
        if not await self.fs._exists(path):
            return None
        async with self.fs.open_async(path, "rb") as f:
            data = await f.read()
        return default_serializer.deserialize(data, target_type=TaskResult)

    async def delete(self, task_id: str) -> None:
        path = self._get_path(task_id)
        if await self.fs._exists(path):
            await self.fs._rm(path)

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        raise NotImplementedError(
            "Listing pending tasks is not efficiently supported by FsspecTaskQueue."
        )

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        raise NotImplementedError(
            "Listing failed tasks is not efficiently supported by FsspecTaskQueue."
        )

    async def list_recent_results(self, limit: int) -> List[TaskResult]:
        """
        List the most recent task results.

        NOTE: This implementation is inefficient for large numbers of results
        as it requires listing all files and sorting them by modification time.
        Not recommended for production use with many results.
        """
        try:
            all_results_info = await self.fs._ls(self.base_path, detail=True)
            # Filter out directories if any
            all_results_info = [info for info in all_results_info if info['type'] == 'file']
        except (FileNotFoundError, IndexError):
            return []

        # Sort by modification time, most recent first
        sorted_results_info = sorted(
            all_results_info, key=lambda info: info.get("mtime", 0), reverse=True
        )

        recent_results = []
        for info in sorted_results_info[:limit]:
            path = info["name"]
            try:
                async with self.fs.open_async(path, "rb") as f:
                    data = await f.read()
                result = default_serializer.deserialize(data, target_type=TaskResult)
                recent_results.append(result)
            except Exception:
                # Skip files that can't be read or deserialized
                continue
        return recent_results