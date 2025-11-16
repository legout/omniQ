"""OmniQ - Async task queue for Python."""

from __future__ import annotations

# Public API exports
from .config import Settings, BackendType, SerializerType, get_settings, create_settings
from .core import AsyncOmniQ, OmniQ, AsyncWorkerPool, WorkerPool
from .models import Task, TaskResult, TaskStatus, Schedule

# Version information
__version__ = "0.1.0"


# Convenience imports for common usage patterns
def create_omniq(**kwargs) -> OmniQ:
    """Create a sync OmniQ instance with custom settings.

    Args:
        **kwargs: Settings overrides (e.g., backend='sqlite', db_url='/path/to/db.db')

    Returns:
        OmniQ instance configured with the provided settings
    """
    settings = create_settings(**kwargs)
    return OmniQ(settings)


def create_async_omniq(**kwargs) -> AsyncOmniQ:
    """Create an async OmniQ instance with custom settings.

    Args:
        **kwargs: Settings overrides (e.g., backend='sqlite', db_url='/path/to/db.db')

    Returns:
        AsyncOmniQ instance configured with the provided settings
    """
    settings = create_settings(**kwargs)
    return AsyncOmniQ(settings)


# Default instances for quick access
_default_async_instance: AsyncOmniQ | None = None
_default_sync_instance: OmniQ | None = None


def get_default_async() -> AsyncOmniQ:
    """Get the default AsyncOmniQ instance.

    Returns:
        A cached AsyncOmniQ instance using default settings
    """
    global _default_async_instance
    if _default_async_instance is None:
        _default_async_instance = AsyncOmniQ()
    return _default_async_instance


def get_default_sync() -> OmniQ:
    """Get the default OmniQ instance.

    Returns:
        A cached OmniQ instance using default settings
    """
    global _default_sync_instance
    if _default_sync_instance is None:
        _default_sync_instance = OmniQ()
    return _default_sync_instance


# Convenience functions for common operations
def enqueue(func, *args, **kwargs):
    """Enqueue a task using the default OmniQ instance.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments including:
            - eta: When to execute (default: now)
            - interval: Recurring interval in seconds (optional)
            - max_retries: Maximum retries (default: from settings)
            - timeout: Task timeout (default: from settings)
            - task_id: Custom task ID (optional)

    Returns:
        Task ID
    """
    return get_default_sync().enqueue(func, args, kwargs)


def get_result(task_id, timeout=None):
    """Get task result using the default OmniQ instance.

    Args:
        task_id: Task ID to get result for
        timeout: Maximum time to wait in seconds (default: wait indefinitely)

    Returns:
        TaskResult instance
    """
    return get_default_sync().get_result(task_id, timeout)


# Export all public symbols
__all__ = [
    # Core classes
    "AsyncOmniQ",
    "OmniQ",
    "AsyncWorkerPool",
    "WorkerPool",
    # Models
    "Task",
    "TaskResult",
    "TaskStatus",
    "Schedule",
    # Configuration
    "Settings",
    "BackendType",
    "SerializerType",
    "get_settings",
    "create_settings",
    # Convenience functions
    "create_omniq",
    "create_async_omniq",
    "get_default_async",
    "get_default_sync",
    "enqueue",
    "get_result",
    # Version
    "__version__",
]
