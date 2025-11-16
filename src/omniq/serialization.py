"""Task and result serialization for OmniQ."""

from __future__ import annotations

import json
import warnings
from abc import ABC, abstractmethod
from typing import Any

from .models import Task, TaskResult, TaskStatus, Schedule


class Serializer(ABC):
    """Abstract serializer interface for OmniQ tasks and results."""

    @abstractmethod
    async def encode_task(self, task: Task) -> bytes:
        """Encode a task to bytes."""
        pass

    @abstractmethod
    async def decode_task(self, data: bytes) -> Task:
        """Decode bytes to a task."""
        pass

    @abstractmethod
    async def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result to bytes."""
        pass

    @abstractmethod
    async def decode_result(self, data: bytes) -> TaskResult:
        """Decode bytes to a result."""
        pass


class MsgspecSerializer(Serializer):
    """JSON-based serializer (msgspec-like fallback).

    This implementation uses Python's built-in json module with a msgspec-compatible
    format. If the actual msgspec library is available, it would be more efficient,
    but this provides a compatible fallback.

    This is the SAFE DEFAULT serializer for OmniQ v1.
    """

    async def encode_task(self, task: Task) -> bytes:
        """Encode a task to bytes using JSON."""
        # Convert task to dict representation compatible with msgspec format
        task_data = {
            "id": task.id,
            "func_path": task.func_path,
            "args": task.args,
            "kwargs": task.kwargs,
            "schedule": {
                "eta": task.schedule.eta.isoformat(),
                "interval": task.schedule.interval,
                "max_retries": task.schedule.max_retries,
                "timeout": task.schedule.timeout,
            },
            "status": task.status.value,
            "attempt": task.attempt,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "metadata": task.metadata,
        }
        return json.dumps(task_data).encode("utf-8")

    async def decode_task(self, data: bytes) -> Task:
        """Decode bytes to a task."""
        from datetime import datetime

        task_data = json.loads(data.decode("utf-8"))

        # Reconstruct schedule
        schedule = Schedule(
            eta=datetime.fromisoformat(task_data["schedule"]["eta"]).replace(
                tzinfo=datetime.fromisoformat(task_data["schedule"]["eta"]).tzinfo
            ),
            interval=task_data["schedule"]["interval"],
            max_retries=task_data["schedule"]["max_retries"],
            timeout=task_data["schedule"]["timeout"],
        )

        # Handle timezone-aware datetime
        created_at = datetime.fromisoformat(task_data["created_at"])
        if created_at.tzinfo is None:
            from datetime import timezone

            created_at = created_at.replace(tzinfo=timezone.utc)

        updated_at = datetime.fromisoformat(task_data["updated_at"])
        if updated_at.tzinfo is None:
            from datetime import timezone

            updated_at = updated_at.replace(tzinfo=timezone.utc)

        return Task(
            id=task_data["id"],
            func_path=task_data["func_path"],
            args=tuple(task_data["args"])
            if isinstance(task_data["args"], list)
            else task_data["args"],
            kwargs=task_data["kwargs"],
            schedule=schedule,
            status=TaskStatus(task_data["status"]),
            attempt=task_data["attempt"],
            created_at=created_at,
            updated_at=updated_at,
            metadata=task_data["metadata"],
        )

    async def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result to bytes using JSON."""
        result_data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "attempt": result.attempt,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat()
            if result.completed_at
            else None,
        }
        return json.dumps(result_data).encode("utf-8")

    async def decode_result(self, data: bytes) -> TaskResult:
        """Decode bytes to a result."""
        from datetime import datetime

        result_data = json.loads(data.decode("utf-8"))

        # Handle timezone-aware datetime
        started_at = None
        if result_data["started_at"]:
            started_at = datetime.fromisoformat(result_data["started_at"])
            if started_at.tzinfo is None:
                from datetime import timezone

                started_at = started_at.replace(tzinfo=timezone.utc)

        completed_at = None
        if result_data["completed_at"]:
            completed_at = datetime.fromisoformat(result_data["completed_at"])
            if completed_at.tzinfo is None:
                from datetime import timezone

                completed_at = completed_at.replace(tzinfo=timezone.utc)

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            attempt=result_data["attempt"],
            started_at=started_at,
            completed_at=completed_at,
        )


class CloudpickleSerializer(Serializer):
    """Cloudpickle-based serializer.

    ⚠️  WARNING: This serializer can execute arbitrary code during deserialization.

    Only use this serializer when you trust the source of serialized data.
    It is provided as an opt-in serializer for cases where msgspec JSON
    serialization is insufficient (e.g., for complex Python objects that
    can't be JSON-serialized).

    This serializer should be explicitly opted into via settings, as it
    poses security risks when used with untrusted data sources.
    """

    def __init__(self):
        """Initialize Cloudpickle serializer with safety warnings."""
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if cloudpickle is available and warn about security."""
        try:
            import cloudpickle

            self.cloudpickle = cloudpickle
        except ImportError:
            raise ImportError(
                "cloudpickle is required for CloudpickleSerializer. "
                "Install it with: pip install cloudpickle"
            )

        # Warn about security implications
        warnings.warn(
            "⚠️  SECURITY WARNING: CloudpickleSerializer can execute arbitrary code "
            "during deserialization. Only use this with trusted data sources. "
            "Consider using MsgspecSerializer for untrusted environments.",
            UserWarning,
            stacklevel=2,
        )

    async def encode_task(self, task: Task) -> bytes:
        """Encode a task to bytes using cloudpickle."""
        return self.cloudpickle.dumps(task)

    async def decode_task(self, data: bytes) -> Task:
        """Decode bytes to a task using cloudpickle."""
        return self.cloudpickle.loads(data)

    async def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result to bytes using cloudpickle."""
        return self.cloudpickle.dumps(result)

    async def decode_result(self, data: bytes) -> TaskResult:
        """Decode bytes to a result using cloudpickle."""
        return self.cloudpickle.loads(data)


def create_serializer(serializer_type: str) -> Serializer:
    """Factory function to create a serializer instance.

    Args:
        serializer_type: Type of serializer ("msgspec" or "cloudpickle")

    Returns:
        Serializer instance

    Raises:
        ValueError: If serializer type is not supported
    """
    serializer_type = serializer_type.lower()

    if serializer_type == "msgspec":
        return MsgspecSerializer()
    elif serializer_type == "cloudpickle":
        return CloudpickleSerializer()
    else:
        raise ValueError(
            f"Unknown serializer type: {serializer_type}. "
            f"Supported types: 'msgspec', 'cloudpickle'"
        )


# Default serializer
DEFAULT_SERIALIZER = MsgspecSerializer()
