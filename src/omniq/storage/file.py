from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

from .base import BaseStorage, NotFoundError, StorageError
from ..models import Task, TaskResult, TaskStatus, transition_status


class Serializer(Protocol):
    """Protocol for task and result serialization."""

    def encode_task(self, task: Task) -> bytes:
        """Encode a task to bytes."""
        ...

    def decode_task(self, data: bytes) -> Task:
        """Decode a task from bytes."""
        ...

    def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result to bytes."""
        ...

    def decode_result(self, data: bytes) -> TaskResult:
        """Decode a result from bytes."""
        ...


class FileStorage(BaseStorage):
    """
    File-based storage backend using local filesystem with atomic operations.

    Uses a directory structure:
    - <base>/queue/ for task files (.task, .running, .done extensions)
    - <base>/results/ for result files (.result extension)
    """

    def __init__(self, base_dir: str | Path, serializer: Serializer):
        self.base_dir = Path(base_dir)
        self.queue_dir = self.base_dir / "queue"
        self.results_dir = self.base_dir / "results"
        self.serializer = serializer

        # Create directories if they don't exist
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def enqueue(self, task: Task) -> str:
        """Write task to queue directory with atomic rename.

        Args:
            task: Task object to enqueue

        Returns:
            Task ID of the enqueued task

        Raises:
            StorageError: If task cannot be written to disk
        """
        task_file = self.queue_dir / f"{task['id']}.task"
        temp_file = self.queue_dir / f"{task['id']}.task.tmp"

        try:
            # Write to temporary file first
            data = self.serializer.encode_task(task)
            temp_file.write_bytes(data)

            # Atomic rename to final location
            os.rename(temp_file, task_file)

            return task["id"]

        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise StorageError(f"Failed to enqueue task {task['id']}: {e}")

    async def dequeue(self, now: datetime) -> Optional[Task]:
        """Find and atomically claim a due task.

        Args:
            now: Current datetime for determining if tasks are due

        Returns:
            Due task if available, None otherwise

        Raises:
            StorageError: If task cannot be dequeued properly
        """
        due_tasks = []

        # Scan for due tasks
        for task_file in self.queue_dir.glob("*.task"):
            try:
                data = task_file.read_bytes()
                task = self.serializer.decode_task(data)

                # Check if task is due
                eta = task["schedule"].get("eta")
                if eta is None or eta <= now:
                    due_tasks.append(
                        (
                            task_file,
                            task,
                            eta or datetime.min.replace(tzinfo=timezone.utc),
                        )
                    )
            except Exception:
                # Skip corrupted files
                continue

        if not due_tasks:
            return None

        # Sort by eta (earliest first) then by creation time for FIFO
        due_tasks.sort(key=lambda x: (x[2], x[1]["created_at"]))

        # Try to claim the earliest due task
        for task_file, task, _ in due_tasks:
            running_file = self.queue_dir / f"{task['id']}.running"

            try:
                # Atomic rename to claim the task
                os.rename(task_file, running_file)

                # Update task status to RUNNING
                updated_task = transition_status(task, TaskStatus.RUNNING)

                # Write updated task back
                data = self.serializer.encode_task(updated_task)
                running_file.write_bytes(data)

                return updated_task

            except OSError:
                # File was claimed by another worker
                continue
            except Exception as e:
                # Restore original file if possible
                if running_file.exists():
                    try:
                        os.rename(running_file, task_file)
                    except OSError:
                        pass
                raise StorageError(f"Failed to dequeue task {task['id']}: {e}")

        return None

    async def mark_running(self, task_id: str) -> None:
        """
        Update task status to RUNNING.

        For FileStorage, this is typically handled during dequeue,
        but we provide the method for interface compatibility.
        """
        running_file = self.queue_dir / f"{task_id}.running"

        if not running_file.exists():
            raise NotFoundError(f"Task {task_id} not found in running state")

        try:
            # Read current task
            data = running_file.read_bytes()
            task = self.serializer.decode_task(data)

            # Update status if not already RUNNING
            if task["status"] != TaskStatus.RUNNING:
                updated_task = transition_status(task, TaskStatus.RUNNING)
                data = self.serializer.encode_task(updated_task)
                running_file.write_bytes(data)

        except Exception as e:
            raise StorageError(f"Failed to mark task {task_id} as running: {e}")

    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """Store result and mark task as completed."""
        running_file = self.queue_dir / f"{task_id}.running"
        done_file = self.queue_dir / f"{task_id}.done"
        result_file = self.results_dir / f"{task_id}.result"

        try:
            # Store the result
            result_data = self.serializer.encode_result(result)
            result_file.write_bytes(result_data)

            # Move task file to done state
            if running_file.exists():
                os.rename(running_file, done_file)
            else:
                # Task might be in .task state if marked done without running
                task_file = self.queue_dir / f"{task_id}.task"
                if task_file.exists():
                    os.rename(task_file, done_file)
                else:
                    raise NotFoundError(f"Task {task_id} not found")

        except Exception as e:
            raise StorageError(f"Failed to mark task {task_id} as done: {e}")

    async def mark_failed(self, task_id: str, error: str, will_retry: bool) -> None:
        """Record failure and update task status."""
        # Find the task file in any possible state
        task_files = [
            self.queue_dir / f"{task_id}.running",
            self.queue_dir / f"{task_id}.task",
            self.queue_dir / f"{task_id}.done",
        ]

        source_file = None
        task = None

        for task_file in task_files:
            if task_file.exists():
                try:
                    data = task_file.read_bytes()
                    task = self.serializer.decode_task(data)
                    source_file = task_file
                    break
                except Exception:
                    # Skip corrupted files and continue
                    continue

        if task is None or source_file is None:
            raise NotFoundError(f"Task {task_id} not found")

        try:
            # First transition to FAILED to represent the completed attempt
            updated_task = transition_status(task, TaskStatus.FAILED)

            # For retryable failures, we'll transition to PENDING after storing the result
            # The reschedule() call will handle the final PENDING status

            # Store error info in a result file
            from ..models import create_failure_result

            failure_result = create_failure_result(
                task_id=task_id,
                error=error,
                attempts=updated_task["attempts"],
                last_attempt_at=updated_task["last_attempt_at"],
            )

            result_file = self.results_dir / f"{task_id}.result"
            result_data = self.serializer.encode_result(failure_result)
            result_file.write_bytes(result_data)

            if will_retry:
                # For retry, keep in FAILED state temporarily
                # The reschedule() call will transition to PENDING and set eta
                target_file = self.queue_dir / f"{task_id}.task"
                data = self.serializer.encode_task(updated_task)
                target_file.write_bytes(data)

                # Remove old file if different
                if source_file != target_file and source_file.exists():
                    source_file.unlink()
            else:
                # Move to done state for final failure
                done_file = self.queue_dir / f"{task_id}.done"

                # Write updated task with FAILED status to done file
                data = self.serializer.encode_task(updated_task)
                done_file.write_bytes(data)

                # Remove old file if different
                if source_file != done_file and source_file.exists():
                    source_file.unlink()

        except Exception as e:
            raise StorageError(f"Failed to mark task {task_id} as failed: {e}")

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve task result by ID."""
        result_file = self.results_dir / f"{task_id}.result"

        if not result_file.exists():
            return None

        try:
            data = result_file.read_bytes()
            return self.serializer.decode_result(data)
        except Exception as e:
            raise StorageError(f"Failed to read result for task {task_id}: {e}")

    async def purge_results(self, older_than: datetime) -> int:
        """Remove old result files."""
        count = 0

        try:
            for result_file in self.results_dir.glob("*.result"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(
                        result_file.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < older_than:
                        result_file.unlink()
                        count += 1
                except OSError:
                    # Skip files that can't be accessed
                    continue

        except Exception as e:
            raise StorageError(f"Failed to purge results: {e}")

        return count

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID from any state file."""
        # Check all possible task file locations in order of preference
        task_files = [
            self.queue_dir / f"{task_id}.running",
            self.queue_dir / f"{task_id}.task",
            self.queue_dir / f"{task_id}.done",
        ]

        for task_file in task_files:
            if task_file.exists():
                try:
                    data = task_file.read_bytes()
                    task = self.serializer.decode_task(data)
                    return task
                except Exception as e:
                    # Skip corrupted files and continue
                    continue

        # Task not found
        return None

    async def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: Optional[int] = 25
    ) -> list[Task]:
        """
        List tasks from filesystem with optional filtering.

        Args:
            status: Filter by task status (optional)
            limit: Maximum number of tasks to return (optional, default 25)

        Returns:
            List of Task dictionaries, sorted by creation time (newest first)
        """
        tasks = []

        # Check all possible task file extensions for each status
        # .task for PENDING, .running for RUNNING, .done for SUCCESS/FAILED
        for pattern in ["*.task", "*.running", "*.done"]:
            for task_file in self.queue_dir.glob(pattern):
                try:
                    data = task_file.read_bytes()
                    task = self.serializer.decode_task(data)

                    # Apply status filter if specified
                    if status is not None and task["status"] != status:
                        continue

                    tasks.append(task)

                    # Apply limit if specified
                    if limit is not None and len(tasks) >= limit:
                        return tasks

                except Exception:
                    # Skip corrupted files
                    continue

        # Sort by created_at (newest first) for consistency across backends
        tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return tasks

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Update task eta for future execution."""
        running_file = self.queue_dir / f"{task_id}.running"
        task_file = self.queue_dir / f"{task_id}.task"

        # Find the task file
        source_file = None
        if running_file.exists():
            source_file = running_file
        elif task_file.exists():
            source_file = task_file
        else:
            raise NotFoundError(f"Task {task_id} not found")

        try:
            # Read and update task
            data = source_file.read_bytes()
            task = self.serializer.decode_task(data)

            # Update eta
            task["schedule"]["eta"] = new_eta

            # For rescheduling, handle status transition properly
            # If task is RUNNING or FAILED, transition to PENDING for rescheduling
            if task["status"] in [TaskStatus.RUNNING, TaskStatus.FAILED]:
                # Create a new task with PENDING status for rescheduling
                updated_task = task.copy()
                updated_task["status"] = TaskStatus.PENDING
                updated_task["updated_at"] = datetime.now(timezone.utc)
            else:
                # For other statuses, use normal transition
                updated_task = transition_status(task, TaskStatus.PENDING)

            # Write back to .task file for future dequeue
            new_task_file = self.queue_dir / f"{task_id}.task"
            data = self.serializer.encode_task(updated_task)
            new_task_file.write_bytes(data)

            # Remove old file if different
            if source_file != new_task_file and source_file.exists():
                source_file.unlink()

        except Exception as e:
            raise StorageError(f"Failed to reschedule task {task_id}: {e}")

    async def close(self) -> None:
        """
        Close the file storage backend.

        File storage doesn't require explicit resource cleanup,
        but the method is provided for interface consistency.
        """
        pass
