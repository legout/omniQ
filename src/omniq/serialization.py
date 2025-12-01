from __future__ import annotations

from datetime import timedelta
from typing import Any, Protocol

from .models import Task, TaskResult


def serialize_timedelta(td: timedelta) -> dict:
    """Serialize a timedelta to a dictionary for JSON serialization."""
    return {"type": "timedelta", "total_seconds": td.total_seconds()}


def deserialize_timedelta(data: dict) -> timedelta:
    """Deserialize a timedelta from a dictionary."""
    if data.get("type") == "timedelta":
        return timedelta(seconds=data["total_seconds"])
    raise ValueError("Invalid timedelta data")


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


class JSONSerializer:
    """
    Simple JSON serializer for basic testing.

    Uses standard library json module for basic serialization.
    Limited to JSON-serializable types.
    """

    def __init__(self):
        import json
        from datetime import datetime

        self._json = json

        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, timedelta):
                return serialize_timedelta(obj)
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable"
            )

        def datetime_object_hook(d):
            # Check if this is a timedelta serialization
            if d.get("type") == "timedelta" and "total_seconds" in d:
                return deserialize_timedelta(d)
            return d

        self._datetime_converter = datetime_converter
        self._datetime_object_hook = datetime_object_hook

    def encode_task(self, task: Task) -> bytes:
        """Encode a task using JSON."""
        try:
            return self._json.dumps(task, default=self._datetime_converter).encode(
                "utf-8"
            )
        except Exception as e:
            raise ValueError(f"Failed to encode task with JSON: {e}")

    def decode_task(self, data: bytes) -> Task:
        """Decode a task using JSON."""
        try:
            return self._json.loads(
                data.decode("utf-8"), object_hook=self._datetime_object_hook
            )
        except Exception as e:
            raise ValueError(f"Failed to decode task with JSON: {e}")

    def encode_result(self, result: TaskResult) -> bytes:
        """Encode a result using JSON."""
        try:
            return self._json.dumps(result, default=self._datetime_converter).encode(
                "utf-8"
            )
        except Exception as e:
            raise ValueError(f"Failed to encode result with JSON: {e}")

    def decode_result(self, data: bytes) -> TaskResult:
        """Decode a result using JSON."""
        try:
            return self._json.loads(
                data.decode("utf-8"), object_hook=self._datetime_object_hook
            )
        except Exception as e:
            raise ValueError(f"Failed to decode result with JSON: {e}")
