"""Enhanced logging configuration for OmniQ library using Loguru with v1 compliance."""

import os
import sys
import json
import time
from typing import Optional, ContextManager, Any
from loguru import logger as loguru_logger

# Global configuration state
_configured = False


def configure(
    level: str = "INFO",
    format: Optional[str] = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "gz",
) -> None:
    """Configure OmniQ logging with smart defaults."""
    global _configured

    # Get environment configuration
    env_level = os.getenv("OMNIQ_LOG_LEVEL", level).upper()
    env_mode = os.getenv("OMNIQ_LOG_MODE", "DEV").upper()
    env_file = os.getenv("OMNIQ_LOG_FILE", "logs/omniq.log")
    env_rotation = os.getenv("OMNIQ_LOG_ROTATION", rotation)
    env_retention = os.getenv("OMNIQ_LOG_RETENTION", retention)

    # Remove default handler
    loguru_logger.remove()

    # Determine format based on mode
    if format is None:
        if env_mode == "PROD":
            format_str = "{message}"  # JSON via serialize
        else:
            format_str = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )
    else:
        format_str = format

    # Add console handler for DEV mode
    if env_mode == "DEV":
        loguru_logger.add(sys.stderr, format=format_str, level=env_level, colorize=True)

    # Add file handler for PROD mode or when OMNIQ_LOG_FILE is set
    if env_mode == "PROD" or os.getenv("OMNIQ_LOG_FILE"):
        loguru_logger.add(
            env_file,
            format=format_str,
            level=env_level,
            rotation=env_rotation,
            retention=env_retention,
            compression=compression,
            serialize=(env_mode == "PROD"),
        )

    _configured = True


def get_logger(name: str = "omniq") -> Any:
    """Get configured logger instance."""
    if not _configured:
        configure()
    return loguru_logger.bind(name=name)


def task_context(task_id: str, operation: str) -> ContextManager[Any]:
    """Context manager for task execution logging with correlation ID."""
    from contextlib import contextmanager

    @contextmanager
    def _task_context() -> Any:
        start_time = time.time()
        task_logger = get_logger().bind(
            task_id=task_id, operation=operation, correlation_id=task_id
        )

        task_logger.info(f"Task {operation} started")
        try:
            yield task_logger
            duration = time.time() - start_time
            task_logger.info(f"Task {operation} completed in {duration:.3f}s")
        except Exception as e:
            duration = time.time() - start_time
            task_logger.error(f"Task {operation} failed after {duration:.3f}s: {e}")
            raise

    return _task_context()


def bind_task(task_id: str, **kwargs) -> Any:
    """Bind correlation ID and additional context to logger."""
    return get_logger().bind(task_id=task_id, correlation_id=task_id, **kwargs)


# Backward compatibility functions
def log_task_enqueued(task_id: str, func_path: str) -> None:
    """Log task enqueuing event."""
    get_logger().info(f"Task enqueued: {task_id} -> {func_path}")


def log_task_started(task_id: str, attempt: int) -> None:
    """Log task start event."""
    get_logger().info(f"Task started: {task_id} (attempt {attempt})")


def log_task_completed(task_id: str, attempts: int) -> None:
    """Log task completion event."""
    get_logger().info(f"Task completed: {task_id} after {attempts} attempts")


def log_task_failed(task_id: str, error: str, will_retry: bool) -> None:
    """Log task failure event."""
    logger = get_logger()
    if will_retry:
        logger.warning(f"Task failed (will retry): {task_id} - {error}")
    else:
        logger.error(f"Task failed (final): {task_id} - {error}")


def log_task_retry(task_id: str, attempt: int, next_eta) -> None:
    """Log task retry event."""
    get_logger().info(
        f"Task retry scheduled: {task_id} (attempt {attempt}) at {next_eta}"
    )


def log_worker_started(concurrency: int) -> None:
    """Log worker start event."""
    get_logger().info(f"Worker started with concurrency: {concurrency}")


def log_worker_stopped() -> None:
    """Log worker stop event."""
    get_logger().info("Worker stopped")


def log_storage_error(operation: str, error: str) -> None:
    """Log storage operation error."""
    get_logger().error(f"Storage error during {operation}: {error}")


def log_serialization_error(operation: str, error: str) -> None:
    """Log serialization error."""
    get_logger().error(f"Serialization error during {operation}: {error}")


# Initialize logging on import
configure()
