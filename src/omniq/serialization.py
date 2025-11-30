from __future__ import annotations

from typing import Any, Protocol

from .models import Task, TaskResult


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


class MsgspecSerializer:
    """
    Safe serializer using msgspec for structured data.

    Provides fast, secure serialization for common Python types.
    Cannot serialize arbitrary Python objects - this is intentional for security.
    """

    def __init__(self):
        try:
            import msgspec
        except ImportError as e:
            raise ImportError(
                "msgspec is required for MsgspecSerializer. "
                "Install it with: pip install msgspec"
            ) from e

        self._task_encoder = msgspec.json.Encoder(type=Task)
        self._task_decoder = msgspec.json.Decoder(type=Task)
        self._result_encoder = msgspec.json.Encoder(type=TaskResult)
        self._result_decoder = msgspec.json.Decoder(type=TaskResult)

    def encode_task(self, task: Task) -> bytes:
        """Encode a task using msgspec JSON."""
        try:
            return self._task_encoder.encode(task)
        except Exception as e:
            raise ValueError(f"Failed to encode task with msgspec: {e}")

    def decode_task(self, data: bytes) -> Task:
        """Decode a task using msgspec JSON."""
        try:
            return self._task_decoder.decode(data)
        except Exception as e:
            raise ValueError(f"Failed to decode task with msgspec: {e}")

    def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result using msgspec JSON."""
        try:
            return self._result_encoder.encode(result)
        except Exception as e:
            raise ValueError(f"Failed to encode result with msgspec: {e}")

    def decode_result(self, data: bytes) -> TaskResult:
        """Decode a result using msgspec JSON."""
        try:
            return self._result_decoder.decode(data)
        except Exception as e:
            raise ValueError(f"Failed to decode result with msgspec: {e}")


class CloudpickleSerializer:
    """
    Unsafe serializer using cloudpickle for arbitrary Python objects.

    Can serialize almost any Python object, including functions, classes, etc.
    This is unsafe for untrusted inputs and should only be used in trusted environments.
    """

    def __init__(self):
        try:
            import cloudpickle
        except ImportError as e:
            raise ImportError(
                "cloudpickle is required for CloudpickleSerializer. "
                "Install it with: pip install cloudpickle"
            ) from e

        self._cloudpickle = cloudpickle

    def encode_task(self, task: Task) -> bytes:
        """Encode a task using cloudpickle."""
        try:
            return self._cloudpickle.dumps(task)
        except Exception as e:
            raise ValueError(f"Failed to encode task with cloudpickle: {e}")

    def decode_task(self, data: bytes) -> Task:
        """Decode a task using cloudpickle."""
        try:
            return self._cloudpickle.loads(data)
        except Exception as e:
            raise ValueError(f"Failed to decode task with cloudpickle: {e}")

    def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result using cloudpickle."""
        try:
            return self._cloudpickle.dumps(result)
        except Exception as e:
            raise ValueError(f"Failed to encode result with cloudpickle: {e}")

    def decode_result(self, data: bytes) -> TaskResult:
        """Decode a result using cloudpickle."""
        try:
            return self._cloudpickle.loads(data)
        except Exception as e:
            raise ValueError(f"Failed to decode result with cloudpickle: {e}")
