"""Core public API for OmniQ."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from .config import Settings, get_settings, BackendType
from .models import Task, TaskResult
from .serialization import create_serializer
from .storage.base import BaseStorage
from .storage.file import FileStorage
from .storage.sqlite import SQLiteStorage

# Import worker pool classes from worker module
from .worker import AsyncWorkerPool, WorkerPool


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

        # Configure loguru log level
        self._configure_log_level()

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

    def _configure_log_level(self) -> None:
        """Configure loguru log level based on settings."""
        # Remove default handler and add custom one with configured level
        logger.remove()
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level=self.settings.log_level.upper(),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )

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

        logger.debug(f"Enqueueing task {task.id}: {task.func_path}")

        # Enqueue task
        await self.storage.enqueue(task)

        logger.info(f"Task {task.id} enqueued successfully")
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
        from .worker import AsyncWorkerPool

        return AsyncWorkerPool(
            storage=self.storage,
            concurrency=max_workers,
        )

    async def purge_expired_results(self) -> int:
        """Clean up old task results based on the configured result TTL.

        This method computes a cutoff time using the current result_ttl setting
        and delegates to the storage backend to purge expired results.

        Returns:
            The number of results that were purged

        Raises:
            Any storage-specific errors
        """
        from datetime import datetime, timezone

        # Compute cutoff time: current time minus result_ttl
        now = datetime.now(timezone.utc)
        older_than = now - timedelta(seconds=self.settings.result_ttl)

        logger.info(
            f"Purging results older than {older_than} (result_ttl={self.settings.result_ttl}s)"
        )

        # Delegate to storage backend
        purged_count = await self.storage.purge_results(older_than)

        logger.info(f"Purged {purged_count} expired results")
        return purged_count

    async def close(self) -> None:
        """Close the AsyncOmniQ instance and cleanup resources."""
        if self._storage_instance:
            await self._storage_instance.close()
        logger.info("AsyncOmniQ closed")


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
        return WorkerPool(
            storage=self._async_instance.storage,
            concurrency=max_workers,
        )

    def purge_expired_results(self) -> int:
        """Clean up old task results based on the configured result TTL (sync version).

        This method computes a cutoff time using the current result_ttl setting
        and delegates to the storage backend to purge expired results.

        Returns:
            The number of results that were purged

        Raises:
            Any storage-specific errors
        """
        self._ensure_event_loop()
        return asyncio.run(self._async_instance.purge_expired_results())

    def close(self) -> None:
        """Close the OmniQ instance and cleanup resources."""
        asyncio.run(self._async_instance.close())
