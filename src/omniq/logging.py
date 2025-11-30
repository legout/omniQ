"""Logging configuration for OmniQ library."""

import logging
import os
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get the OmniQ library logger."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("omniq")
        configure_logging()
    return _logger


def configure_logging(level: Optional[str] = None) -> None:
    """
    Configure OmniQ logging with the specified level.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses OMNIQ_LOG_LEVEL environment variable or defaults to INFO.
    """
    logger = logging.getLogger("omniq")

    # Determine log level
    if level is None:
        level = os.getenv("OMNIQ_LOG_LEVEL", "INFO").upper()

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Set logger level
    logger.setLevel(numeric_level)

    # Only configure handler if none exists to avoid duplicate handlers
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(numeric_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False


def log_task_enqueued(task_id: str, func_path: str) -> None:
    """Log task enqueuing event."""
    logger = get_logger()
    logger.info(f"Task enqueued: {task_id} -> {func_path}")


def log_task_started(task_id: str, attempt: int) -> None:
    """Log task start event."""
    logger = get_logger()
    logger.info(f"Task started: {task_id} (attempt {attempt})")


def log_task_completed(task_id: str, attempts: int) -> None:
    """Log task completion event."""
    logger = get_logger()
    logger.info(f"Task completed: {task_id} after {attempts} attempts")


def log_task_failed(task_id: str, error: str, will_retry: bool) -> None:
    """Log task failure event."""
    logger = get_logger()
    if will_retry:
        logger.warning(f"Task failed (will retry): {task_id} - {error}")
    else:
        logger.error(f"Task failed (final): {task_id} - {error}")


def log_task_retry(task_id: str, attempt: int, next_eta) -> None:
    """Log task retry event."""
    logger = get_logger()
    logger.info(f"Task retry scheduled: {task_id} (attempt {attempt}) at {next_eta}")


def log_worker_started(concurrency: int) -> None:
    """Log worker start event."""
    logger = get_logger()
    logger.info(f"Worker started with concurrency: {concurrency}")


def log_worker_stopped() -> None:
    """Log worker stop event."""
    logger = get_logger()
    logger.info("Worker stopped")


def log_storage_error(operation: str, error: str) -> None:
    """Log storage operation error."""
    logger = get_logger()
    logger.error(f"Storage error during {operation}: {error}")


def log_serialization_error(operation: str, error: str) -> None:
    """Log serialization error."""
    logger = get_logger()
    logger.error(f"Serialization error during {operation}: {error}")
