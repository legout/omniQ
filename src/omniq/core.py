"""Core public API for OmniQ."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .config import Settings, get_settings, BackendType
from .models import Task, TaskResult
from .serialization import create_serializer
from .storage.base import BaseStorage
from .storage.file import FileStorage
from .storage.sqlite import SQLiteStorage


class AsyncOmniQ:
    """Async interface for OmniQ.

    This is the main async interface for interacting with OmniQ.
    It provides methods for enqueueing tasks, getting results, and managing workers.
    """

    def __init__(
        self, settings: Optional[Settings] = None, storage: Optional[BaseStorage] = None
    ):
        """Initialize AsyncOmniQ.

        Args:
            settings: Configuration settings. If None, loads from environment.
            storage: Pre-configured storage backend. If None, creates from settings.
        """
        # Load settings if not provided
        if settings is None:
            from .config import get_settings

            self.settings = get_settings()
        else:
            self.settings = settings
        self._storage = storage
        self._serializer = create_serializer(self.settings.serializer.value)
        self._log = logging.getLogger(__name__)

        # Initialize logging
        self._configure_logging()

        # Cache for storage backend
        self._storage_instance: Optional[BaseStorage] = None

    @property
    def storage(self) -> BaseStorage:
        """Get or create the storage backend."""
        if self._storage_instance is None:
            self._storage_instance = self._create_storage()
        return self._storage_instance

    def _create_storage(self) -> BaseStorage:
        """Create storage backend based on settings."""
        if self._storage:
            return self._storage

        if self.settings.backend == BackendType.FILE:
            return FileStorage(
                base_dir=self.settings.base_dir,
                serializer=self._serializer,
            )
        elif self.settings.backend == BackendType.SQLITE:
            return SQLiteStorage(
                db_path=Path(self.settings.db_url)
                if self.settings.db_url != ":memory:"
                else Path(":memory:"),
                serializer=self._serializer,
            )
        else:
            raise ValueError(f"Unsupported backend: {self.settings.backend}")

    def _configure_logging(self) -> None:
        """Configure logging based on settings."""
        import logging

        # Set log level
        log_level = getattr(logging, self.settings.log_level.upper(), logging.INFO)
        logging.getLogger("omniq").setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create console handler if none exists
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger = logging.getLogger("omniq")
        if not logger.handlers:
            logger.addHandler(handler)

        logger.info(
            f"AsyncOmniQ initialized with {self.settings.backend} backend, log level: {self.settings.log_level}"
        )

    async def enqueue(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """Enqueue a task for execution.

        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            eta: When to execute the task. If None, executes immediately.
            interval: Fixed interval for recurring tasks (seconds)
            max_retries: Maximum number of retries. If None, uses default.
            timeout: Task timeout in seconds. If None, uses default.
            task_id: Custom task ID. If None, auto-generated.

        Returns:
            The task ID
        """
        # Use defaults from settings
        if max_retries is None:
            max_retries = self.settings.default_max_retries
        if timeout is None:
            timeout = self.settings.default_timeout
        if eta is None:
            eta = datetime.now(timezone.utc)

        # Create task
        task = Task.create(
            func=func,
            args=args,
            kwargs=kwargs or {},
            eta=eta,
            interval=interval,
            max_retries=max_retries or 0,
            timeout=timeout,
            task_id=task_id,
        )

        self._log.debug(f"Enqueueing task {task.id}: {task.func_path}")

        # Enqueue task
        await self.storage.enqueue(task)

        self._log.info(f"Task {task.id} enqueued successfully")
        return task.id

    async def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> TaskResult:
        """Get the result of a task.

        Args:
            task_id: The task ID to get results for
            timeout: Maximum time to wait for result in seconds.
                    If None, waits indefinitely.

        Returns:
            The task result

        Raises:
            asyncio.TimeoutError: If timeout is reached
        """

        async def _wait_for_result():
            while True:
                result = await self.storage.get_result(task_id)
                if result is not None:
                    return result
                await asyncio.sleep(0.1)  # Poll every 100ms

        if timeout is None:
            return await _wait_for_result()
        else:
            return await asyncio.wait_for(_wait_for_result(), timeout=timeout)

    async def worker(self, max_workers: int = 1) -> AsyncWorkerPool:
        """Create a worker pool for processing tasks.

        Args:
            max_workers: Maximum number of concurrent workers

        Returns:
            An AsyncWorkerPool instance
        """
        return AsyncWorkerPool(
            storage=self.storage,
            concurrency=max_workers,
        )

    async def close(self) -> None:
        """Close the AsyncOmniQ instance and cleanup resources."""
        if self._storage_instance:
            await self._storage_instance.close()
        self._log.info("AsyncOmniQ closed")


class OmniQ:
    """Sync wrapper for AsyncOmniQ.

    This provides a synchronous interface for users who prefer
    blocking API calls over async/await.
    """

    def __init__(
        self, settings: Optional[Settings] = None, storage: Optional[BaseStorage] = None
    ):
        """Initialize OmniQ.

        Args:
            settings: Configuration settings. If None, loads from environment.
            storage: Pre-configured storage backend. If None, creates from settings.
        """
        self._async_instance = AsyncOmniQ(settings, storage)
        self._runner = None
        self._log = logging.getLogger(__name__)

    @property
    def _loop(self) -> asyncio.AbstractEventLoop:
        """Get or create the event loop."""
        try:
            # Try to get the current running loop
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # We're already in an async context, create a new event loop
                # This is a limitation - users shouldn't mix sync/async calls
                raise RuntimeError(
                    "OmniQ is already running in an async context. "
                    "Use AsyncOmniQ directly or complete async operations before using sync API."
                )
            return loop
        except RuntimeError:
            # No running loop, we can create a new one
            return asyncio.new_event_loop()

    def _ensure_event_loop(self) -> None:
        """Ensure we have an event loop for async operations."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop running, we can proceed
            pass
        else:
            raise RuntimeError(
                "Cannot use sync OmniQ in an async context. "
                "Either complete async operations or use AsyncOmniQ directly."
            )

    def enqueue(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        eta: Optional[datetime] = None,
        interval: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """Enqueue a task for execution (sync version).

        Args:
            func: The function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            eta: When to execute the task. If None, executes immediately.
            interval: Fixed interval for recurring tasks (seconds)
            max_retries: Maximum number of retries. If None, uses default.
            timeout: Task timeout in seconds. If None, uses default.
            task_id: Custom task ID. If None, auto-generated.

        Returns:
            The task ID
        """
        self._ensure_event_loop()
        return asyncio.run(
            self._async_instance.enqueue(
                func, args, kwargs, eta, interval, max_retries, timeout, task_id
            )
        )

    def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> TaskResult:
        """Get the result of a task (sync version).

        Args:
            task_id: The task ID to get results for
            timeout: Maximum time to wait for result in seconds.
                    If None, waits indefinitely.

        Returns:
            The task result

        Raises:
            asyncio.TimeoutError: If timeout is reached
        """
        self._ensure_event_loop()
        return asyncio.run(self._async_instance.get_result(task_id, timeout))

    def worker(self, max_workers: int = 1) -> WorkerPool:
        """Create a worker pool for processing tasks (sync version).

        Args:
            max_workers: Maximum number of concurrent workers

        Returns:
            A WorkerPool instance
        """
        self._ensure_event_loop()
        async_pool = asyncio.run(self._async_instance.worker(max_workers))
        return WorkerPool(async_pool)

    def close(self) -> None:
        """Close the OmniQ instance and cleanup resources."""
        asyncio.run(self._async_instance.close())


class AsyncWorkerPool:
    """Async worker pool for processing tasks.

    This is a placeholder implementation for the worker pool feature.
    Full implementation would be in a separate worker.py module.
    """

    def __init__(
        self,
        storage: BaseStorage,
        serializer,
        max_workers: int = 1,
        settings: Optional[Settings] = None,
    ):
        """Initialize AsyncWorkerPool.

        Args:
            storage: Storage backend to use
            serializer: Serializer for tasks/results
            max_workers: Maximum number of concurrent workers
            settings: Configuration settings
        """
        self.storage = storage
        self.serializer = serializer
        self.max_workers = max_workers
        self.settings = settings or get_settings()
        self._running = False
        self._workers = []
        self._log = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return

        self._running = True
        self._log.info(f"Starting AsyncWorkerPool with {self.max_workers} workers")

        # This would start actual worker tasks in a full implementation
        # For now, it's a placeholder

    async def stop(self) -> None:
        """Stop the worker pool."""
        if not self._running:
            return

        self._running = False
        self._log.info("Stopping AsyncWorkerPool")

        # This would stop worker tasks in a full implementation


class WorkerPool:
    """Sync wrapper for AsyncWorkerPool."""

    def __init__(self, async_pool: AsyncWorkerPool):
        """Initialize WorkerPool.

        Args:
            async_pool: The async worker pool to wrap
        """
        self._async_pool = async_pool

    def start(self) -> None:
        """Start the worker pool (sync version)."""
        asyncio.run(self._async_pool.start())

    def stop(self) -> None:
        """Stop the worker pool (sync version)."""
        asyncio.run(self._async_pool.stop())
