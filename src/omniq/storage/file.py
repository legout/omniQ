"""File-based storage backend for OmniQ tasks and results."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models import Task, TaskResult, TaskStatus
from .base import BaseStorage, Serializer, TaskError


class FileStorage(BaseStorage):
    """File-based storage implementation using local filesystem.

    Directory layout:
    - <base_dir>/queue/      - Task files (.task, .running, .done)
    - <base_dir>/results/    - Result files (.result)
    """

    def __init__(
        self,
        base_dir: Path,
        serializer: Serializer,
    ):
        self.base_dir = Path(base_dir)
        self.queue_dir = self.base_dir / "queue"
        self.results_dir = self.base_dir / "results"
        self.serializer = serializer

        # Create directories
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def enqueue(self, task: Task) -> str:
        """Add a task to the queue using atomic write."""
        task_file = self.queue_dir / f"{task.id}.task"
        temp_file = self.queue_dir / f"{task.id}.task.tmp"

        # Serialize task to bytes
        data = await self.serializer.encode_task(task)

        # Write to temp file first
        await self._async_write(temp_file, data)

        # Atomic rename to final location
        try:
            temp_file.rename(task_file)
        except FileNotFoundError:
            # Handle race condition where temp file was removed
            pass

        return task.id

    async def dequeue(self, now: datetime) -> Optional[Task]:
        """Get next due task using atomic rename for claiming."""
        # Find candidate task files
        candidates = []
        for task_file in self.queue_dir.glob("*.task"):
            try:
                # Read and deserialize task
                data = await self._async_read(task_file)
                task = await self.serializer.decode_task(data)

                # Check if task is due
                if task.schedule.eta <= now:
                    candidates.append((task, task_file))
            except (OSError, Exception):
                # Skip corrupted or unreadable files
                continue

        if not candidates:
            return None

        # Sort by ETA (earliest first), then by filename for FIFO
        candidates.sort(key=lambda x: (x[0].schedule.eta, x[1].name))

        # Try to claim the first candidate using atomic rename
        for task, task_file in candidates:
            running_file = task_file.with_suffix(".running")
            try:
                # Atomic rename to claim the task
                task_file.rename(running_file)
                return task
            except FileNotFoundError:
                # Task was claimed by another process, continue to next
                continue

        return None

    async def mark_running(self, task_id: str) -> None:
        """Mark task as running.

        For FileStorage, this is a no-op since dequeue already renamed
        the task file to .running, indicating it's claimed.
        """
        pass

    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """Mark task as completed and save result."""
        running_file = self.queue_dir / f"{task_id}.running"
        done_file = self.queue_dir / f"{task_id}.done"
        result_file = self.results_dir / f"{task_id}.result"

        # Serialize and save result
        data = await self.serializer.encode_result(result)
        await self._async_write(result_file, data)

        # Rename task file to indicate completion
        if running_file.exists():
            try:
                running_file.rename(done_file)
            except FileNotFoundError:
                # File was already moved, ignore
                pass

    async def mark_failed(
        self, task_id: str, error: TaskError, will_retry: bool
    ) -> None:
        """Mark task as failed."""
        running_file = self.queue_dir / f"{task_id}.running"

        if will_retry:
            # Create a retrying result but keep task available for rescheduling
            retry_result = TaskResult.retrying(
                task_id=task_id,
                error=error.error,
                attempt=1,  # Will be updated by caller
                next_eta=datetime.now(timezone.utc),  # Will be updated by caller
            )
        else:
            # Final failure
            retry_result = TaskResult.failure(
                task_id=task_id,
                error=error.error,
                attempt=1,  # Will be updated by caller
            )

        # Save failure result
        result_file = self.results_dir / f"{task_id}.result"
        data = await self.serializer.encode_result(retry_result)
        await self._async_write(result_file, data)

        # Move task file to indicate final state
        if running_file.exists():
            failed_file = self.queue_dir / f"{task_id}.failed"
            try:
                running_file.rename(failed_file)
            except FileNotFoundError:
                pass

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve task result from results directory."""
        result_file = self.results_dir / f"{task_id}.result"

        if not result_file.exists():
            return None

        try:
            data = await self._async_read(result_file)
            return await self.serializer.decode_result(data)
        except (OSError, Exception):
            return None

    async def purge_results(self, older_than: datetime) -> int:
        """Remove old result files."""
        count = 0
        for result_file in self.results_dir.glob("*.result"):
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(
                    result_file.stat().st_mtime, tz=timezone.utc
                )
                if mtime < older_than:
                    result_file.unlink()
                    count += 1
            except (OSError, Exception):
                # Skip files we can't process
                continue

        return count

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Reschedule a task by moving it back to the queue."""
        # Look for task in different possible states
        for suffix in [".running", ".failed", ".done"]:
            task_file = self.queue_dir / f"{task_id}{suffix}"
            if task_file.exists():
                # Move back to queue with updated ETA
                target_file = self.queue_dir / f"{task_id}.task"
                task_file.rename(target_file)
                break
        else:
            raise FileNotFoundError(f"Task {task_id} not found for rescheduling")

    async def close(self) -> None:
        """Close storage (no-op for file storage)."""
        pass

    async def _async_write(self, file_path: Path, data: bytes) -> None:
        """Async file write using thread pool."""

        def _write():
            with open(file_path, "wb") as f:
                f.write(data)

        await self._run_in_thread(_write)

    async def _async_read(self, file_path: Path) -> bytes:
        """Async file read using thread pool."""

        def _read():
            with open(file_path, "rb") as f:
                return f.read()

        return await self._run_in_thread(_read)

    async def _run_in_thread(self, func):
        """Run blocking function in thread pool."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)
