"""
OmniQ - A modular Python task queue library for local and distributed processing.

OmniQ implements an "Async First, Sync Wrapped" architecture where core functionality
is implemented asynchronously with synchronous wrappers for convenience.

Key Features:
- Async-first design with sync wrappers  
- Multiple storage backends (file, memory, SQLite, PostgreSQL, Redis, NATS)
- Intelligent dual serialization (msgspec + dill)
- Comprehensive task lifecycle events
- Flexible scheduling with pause/resume
- Task dependencies and callbacks
- Multiple worker types (async, thread, process, gevent)
- Separation of concerns (queue, results, events)
"""

from .models import (
    Task, TaskDependency, TaskCallback,
    Schedule, ScheduleConfig,
    TaskResult, TaskError,
    TaskEvent, TaskEventType,
    QueueConfig, WorkerConfig, StorageConfig, 
    SerializationConfig, EventConfig, OmniQConfig
)

from .serialization import (
    SerializationDetector, SerializationManager,
    MsgspecSerializer, DillSerializer
)

from .storage import (
    BaseTaskQueue, BaseResultStorage, BaseEventStorage
)

from .events import (
    AsyncEventLogger, EventLogger,
    AsyncEventProcessor, EventProcessor
)

from .workers import (
    BaseWorker, WorkerState,
    AsyncWorker, ThreadWorker, ProcessWorker
)

from .config import (
    ConfigProvider, LoggingConfig,
    get_env_config
)

from .core import AsyncOmniQ, OmniQ

# Version information
__version__ = "0.1.0"
__author__ = "OmniQ Contributors"
__license__ = "MIT"

# Main exports for convenience
__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__license__",
    
    # Core models
    "Task",
    "TaskDependency",
    "TaskCallback", 
    "Schedule",
    "ScheduleConfig",
    "TaskResult",
    "TaskError",
    "TaskEvent",
    "TaskEventType",
    
    # Configuration models
    "QueueConfig",
    "WorkerConfig",
    "StorageConfig",
    "SerializationConfig", 
    "EventConfig",
    "OmniQConfig",
    
    # Serialization
    "SerializationDetector",
    "SerializationManager",
    "MsgspecSerializer",
    "DillSerializer",
    
    # Storage interfaces
    "BaseTaskQueue",
    "BaseResultStorage",
    "BaseEventStorage",
    
    # Event system
    "AsyncEventLogger",
    "EventLogger",
    "AsyncEventProcessor",
    "EventProcessor",
    
    # Workers
    "BaseWorker",
    "WorkerState",
    "AsyncWorker",
    "ThreadWorker",
    "ProcessWorker",
    
    # Configuration
    "ConfigProvider",
    "LoggingConfig",
    "get_env_config",
    
    # Core orchestrator
    "AsyncOmniQ",
    "OmniQ",
]


def get_version() -> str:
    """Get the current version of OmniQ."""
    return __version__


def configure_logging(level: str = "INFO", **kwargs) -> None:
    """
    Configure logging for OmniQ.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, DISABLED)
        **kwargs: Additional logging configuration options
    """
    LoggingConfig.setup_logging(level=level, **kwargs)


def load_config(
    config_file: str = None,
    use_env: bool = True
) -> OmniQConfig:
    """
    Load OmniQ configuration from file and/or environment.
    
    Args:
        config_file: Optional path to YAML config file
        use_env: Whether to load environment variables
    
    Returns:
        Loaded configuration
    """
    provider = ConfigProvider()
    return provider.load_auto(config_file=config_file, use_env=use_env)