"""Logging configuration for OmniQ library using Loguru."""

import os
import sys
from typing import Optional, Any, Dict, Union
from warnings import warn

try:
    from loguru import logger as _loguru_logger

    LOGURU_AVAILABLE = True
except ImportError:
    # Fallback to standard logging if loguru is not available
    import logging

    _loguru_logger = None
    LOGURU_AVAILABLE = False

# Global configuration state
_configured = False
_fallback_logger = None


def get_logger() -> Union[Any, "logging.Logger"]:
    """Get the OmniQ library logger."""
    if LOGURU_AVAILABLE:
        return _loguru_logger
    else:
        # Fallback to standard logging
        import logging

        global _fallback_logger
        if _fallback_logger is None:
            _fallback_logger = logging.getLogger("omniq")
            configure_logging_fallback()
        return _fallback_logger


def configure_logging(
    level: Optional[str] = None,
    format: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
    compression: Optional[str] = None,
    log_file: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Configure OmniQ logging with Loguru.

    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses OMNIQ_LOG_LEVEL or LOGURU_LEVEL environment variable, defaults to INFO.
        format: Log format string. If None, uses default Loguru format.
        rotation: Log rotation configuration (e.g., "10 MB", "1 day").
        retention: Log retention configuration (e.g., "1 week", "10 days").
        compression: Log compression (e.g., "gz", "zip").
        **kwargs: Additional Loguru configuration options.
    """
    global _configured

    if not LOGURU_AVAILABLE:
        configure_logging_fallback(level)
        return

    # Remove default handler
    _loguru_logger.remove()

    # Determine log level
    if level is None:
        # Support both old and new environment variables
        level = (
            os.getenv("OMNIQ_LOG_LEVEL") or os.getenv("LOGURU_LEVEL") or "INFO"
        ).upper()

    # Set default format if not provided - include extra context
    if format is None:
        format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "<dim>{extra}</dim>"
        )

    # Add console handler
    _loguru_logger.add(sys.stderr, level=level, format=format, **kwargs)

    # Add file handler if rotation is specified
    if rotation:
        log_file = log_file or "omniq.log"
        _loguru_logger.add(
            log_file,
            level=level,
            format=format,
            rotation=rotation,
            retention=retention,
            compression=compression,
            **kwargs,
        )

    _configured = True


def configure_logging_fallback(level: Optional[str] = None) -> None:
    """Fallback configuration using standard logging."""
    import logging

    # Determine log level
    if level is None:
        level = os.getenv("OMNIQ_LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure fallback logger
    fallback_logger = logging.getLogger("omniq")
    fallback_logger.setLevel(numeric_level)

    if not fallback_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        fallback_logger.addHandler(handler)
        fallback_logger.propagate = False


def add_structured_context(**context: Any) -> None:
    """
    Add structured context to all subsequent log messages.

    Args:
        **context: Key-value pairs to include in log context.
    """
    if LOGURU_AVAILABLE:
        _loguru_logger.configure(extra=context)
    else:
        # No-op for fallback logging
        pass


# Backward compatibility functions - maintain existing API
def log_task_enqueued(task_id: str, func_path: str) -> None:
    """Log task enqueuing event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(task_id=task_id, func_path=func_path).info(
            "Task enqueued: {task_id} -> {func_path}",
            task_id=task_id,
            func_path=func_path,
        )
    else:
        log_logger.info(f"Task enqueued: {task_id} -> {func_path}")


def log_task_started(task_id: str, attempt: int) -> None:
    """Log task start event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(task_id=task_id, attempt=attempt).info(
            "Task started: {task_id} (attempt {attempt})",
            task_id=task_id,
            attempt=attempt,
        )
    else:
        log_logger.info(f"Task started: {task_id} (attempt {attempt})")


def log_task_completed(task_id: str, attempts: int) -> None:
    """Log task completion event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(task_id=task_id, attempts=attempts).info(
            "Task completed: {task_id} after {attempts} attempts",
            task_id=task_id,
            attempts=attempts,
        )
    else:
        log_logger.info(f"Task completed: {task_id} after {attempts} attempts")


def log_task_failed(task_id: str, error: str, will_retry: bool) -> None:
    """Log task failure event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        bound_logger = log_logger.bind(task_id=task_id, error=error)
        if will_retry:
            bound_logger.warning(
                "Task failed (will retry): {task_id} - {error}",
                task_id=task_id,
                error=error,
            )
        else:
            bound_logger.error(
                "Task failed (final): {task_id} - {error}", task_id=task_id, error=error
            )
    else:
        if will_retry:
            log_logger.warning(f"Task failed (will retry): {task_id} - {error}")
        else:
            log_logger.error(f"Task failed (final): {task_id} - {error}")


def log_task_retry(task_id: str, attempt: int, next_eta) -> None:
    """Log task retry event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(task_id=task_id, attempt=attempt, next_eta=next_eta).info(
            "Task retry scheduled: {task_id} (attempt {attempt}) at {next_eta}",
            task_id=task_id,
            attempt=attempt,
            next_eta=next_eta,
        )
    else:
        log_logger.info(
            f"Task retry scheduled: {task_id} (attempt {attempt}) at {next_eta}"
        )


def log_worker_started(concurrency: int) -> None:
    """Log worker start event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(concurrency=concurrency).info(
            "Worker started with concurrency: {concurrency}", concurrency=concurrency
        )
    else:
        log_logger.info(f"Worker started with concurrency: {concurrency}")


def log_worker_stopped() -> None:
    """Log worker stop event."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.info("Worker stopped")
    else:
        log_logger.info("Worker stopped")


def log_storage_error(operation: str, error: str) -> None:
    """Log storage operation error."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(operation=operation, error=error).error(
            "Storage error during {operation}: {error}",
            operation=operation,
            error=error,
        )
    else:
        log_logger.error(f"Storage error during {operation}: {error}")


def log_serialization_error(operation: str, error: str) -> None:
    """Log serialization error."""
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(operation=operation, error=error).error(
            "Serialization error during {operation}: {error}",
            operation=operation,
            error=error,
        )
    else:
        log_logger.error(f"Serialization error during {operation}: {error}")


# New structured logging functions
def log_structured(level: str, message: str, **kwargs: Any) -> None:
    """
    Log a structured message with contextual data.

    Args:
        level: Log level (trace, debug, info, warning, error, critical).
        message: Log message.
        **kwargs: Structured data to include in log.
    """
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        bound_logger = log_logger.bind(**kwargs)
        log_method = getattr(bound_logger, level.lower(), bound_logger.info)
        log_method(message)
    else:
        # Fallback to string formatting
        context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        log_logger.info(f"{message} | {context_str}")


def log_exception(message: str, **kwargs: Any) -> None:
    """
    Log an exception with full traceback and contextual data.

    Args:
        message: Error message.
        **kwargs: Additional context data.
    """
    log_logger = get_logger()
    if LOGURU_AVAILABLE:
        log_logger.bind(**kwargs).exception(message)
    else:
        import traceback

        log_logger.error(f"{message} | {kwargs}")
        log_logger.error(traceback.format_exc())


# Initialize logging on import
if not _configured:
    configure_logging()
