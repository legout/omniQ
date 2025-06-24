"""
Worker factory module for OmniQ.

This module provides a factory for creating worker instances based on configuration
or task requirements. It supports multiple worker types (async, thread, process, gevent)
and allows for runtime selection.
"""

from typing import Optional, Type, Dict, Any
import os
from omniq.workers.base import BaseWorker
from omniq.workers.pool import WorkerPool

from omniq.workers.async_worker import AsyncWorker
from omniq.workers.thread_worker import ThreadWorker
from omniq.workers.process_worker import ProcessWorker
from omniq.workers.gevent_worker import GeventWorker


class WorkerFactory:
    """
    Factory class for creating worker pools based on the specified worker type.
    Supports configuration via environment variables or direct parameters.
    """

    _worker_types: Dict[str, Type[BaseWorker]] = {}

    @classmethod
    def register_worker_type(cls, worker_type: str, worker_class: Type[BaseWorker]) -> None:
        """
        Register a new worker type with its corresponding class.

        Args:
            worker_type (str): The identifier for the worker type (e.g., 'async', 'thread').
            worker_class (Type[BaseWorker]): The class implementing the worker type.
        """
        cls._worker_types[worker_type] = worker_class

    @classmethod
    def create_worker(
        cls,
        worker_type: Optional[str] = None,
        max_tasks: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> WorkerPool:
        """
        Create a worker pool based on the specified type or configuration.

        Args:
            worker_type (Optional[str]): The type of worker to create. If None, uses environment variable or default.
            max_tasks (Optional[int]): Maximum number of workers in the pool.
            timeout (Optional[float]): Default timeout for task execution in seconds.
            **kwargs: Additional arguments to pass to the worker constructor.

        Returns:
            WorkerPool: A worker pool instance of the specified worker type.

        Raises:
            ValueError: If the specified worker type is not registered or invalid.
        """
        # Determine worker type from parameter, environment variable, or default
        if worker_type is None:
            worker_type = os.getenv("OMNIQ_DEFAULT_WORKER", "async")

        # Get max_tasks from parameter, environment variable, or default
        if max_tasks is None:
            max_tasks_env = os.getenv("OMNIQ_MAX_WORKERS")
            max_tasks = int(max_tasks_env) if max_tasks_env is not None else 10

        if worker_type not in cls._worker_types:
            raise ValueError(f"Unknown worker type: {worker_type}. Available types: {list(cls._worker_types.keys())}")

        return WorkerPool(worker_type=worker_type, max_workers=max_tasks, timeout=timeout, **kwargs)

    @classmethod
    def get_available_worker_types(cls) -> list[str]:
        """
        Get a list of available worker types.

        Returns:
            list[str]: List of registered worker type identifiers.
        """
        return list(cls._worker_types.keys())


# Register available worker types

WorkerFactory.register_worker_type("async", AsyncWorker)
WorkerFactory.register_worker_type("thread", ThreadWorker)
WorkerFactory.register_worker_type("process", ProcessWorker)
WorkerFactory.register_worker_type("gevent", GeventWorker)
