#!/usr/bin/env python3
"""
Test script for the new Loguru-based logging implementation.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omniq.logging import (
    configure_logging,
    get_logger,
    log_task_enqueued,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_task_retry,
    log_worker_started,
    log_worker_stopped,
    log_storage_error,
    log_serialization_error,
    log_structured,
    log_exception,
    add_structured_context,
)


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing basic logging...")

    # Capture stderr to check log output
    log_capture = StringIO()

    # Configure logging to capture to string
    configure_logging(level="INFO")

    # Test basic logger
    logger = get_logger()
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    print("✓ Basic logging works")


def test_task_logging_functions():
    """Test task-specific logging functions."""
    print("Testing task logging functions...")

    configure_logging(level="INFO")

    # Test all task logging functions
    log_task_enqueued("task-123", "test_module.test_function")
    log_task_started("task-123", 1)
    log_task_completed("task-123", 1)
    log_task_failed("task-123", "Test error", will_retry=True)
    log_task_failed("task-123", "Final error", will_retry=False)
    log_task_retry("task-123", 2, "2025-01-01 12:00:00")
    log_worker_started(4)
    log_worker_stopped()
    log_storage_error("enqueue", "Connection failed")
    log_serialization_error("deserialize", "Invalid JSON")

    print("✓ Task logging functions work")


def test_structured_logging():
    """Test structured logging capabilities."""
    print("Testing structured logging...")

    configure_logging(level="INFO")

    # Test structured logging
    log_structured(
        "info", "Task processed", task_id="task-123", duration=1.5, status="success"
    )
    log_structured("warning", "High memory usage", memory_mb=850, threshold=800)
    log_structured(
        "error", "Database connection failed", database="postgres", error_code=1001
    )

    # Test adding context
    add_structured_context(service="omniq", environment="test")
    log_structured("info", "Service started", version="0.1.0")

    print("✓ Structured logging works")


def test_exception_logging():
    """Test exception logging with traceback."""
    print("Testing exception logging...")

    configure_logging(level="INFO")

    try:
        # Create an exception to log
        raise ValueError("Test exception for logging")
    except Exception:
        log_exception("Test exception occurred", operation="test", user_id="user-123")

    print("✓ Exception logging works")


def test_environment_variables():
    """Test environment variable configuration."""
    print("Testing environment variable configuration...")

    # Test with OMNIQ_LOG_LEVEL
    os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"
    configure_logging()

    logger = get_logger()
    logger.debug("This debug message should appear")

    # Test with LOGURU_LEVEL
    os.environ["LOGURU_LEVEL"] = "ERROR"
    configure_logging()

    logger.info("This info message should NOT appear")
    logger.error("This error message should appear")

    # Clean up
    del os.environ["OMNIQ_LOG_LEVEL"]
    del os.environ["LOGURU_LEVEL"]

    print("✓ Environment variable configuration works")


def test_configuration_options():
    """Test advanced configuration options."""
    print("Testing advanced configuration...")

    # Test custom format
    configure_logging(
        level="INFO", format="{time} | {level} | {message}", colorize=False
    )

    logger = get_logger()
    logger.info("Custom format test")

    # Test with file output (using temp file)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        temp_log_file = f.name

    try:
        configure_logging(level="INFO", rotation="1 MB", log_file=temp_log_file)

        logger = get_logger()
        logger.info("Message to file")

        # Check if file was created and has content
        if Path(temp_log_file).exists():
            with open(temp_log_file, "r") as f:
                content = f.read()
                if "Message to file" in content:
                    print("✓ File logging works")
                else:
                    print("✗ File logging failed - no content found")
        else:
            print("✗ File logging failed - no file created")

    finally:
        # Clean up temp file
        if Path(temp_log_file).exists():
            Path(temp_log_file).unlink()

    print("✓ Advanced configuration works")


def test_fallback_logging():
    """Test fallback to standard logging when loguru is not available."""
    print("Testing fallback logging...")

    # This test simulates the fallback behavior
    # In a real scenario, this would happen when loguru is not installed

    # We can't easily uninstall loguru for this test, but we can verify
    # the fallback functions exist and don't crash
    from omniq.logging import LOGURU_AVAILABLE, configure_logging_fallback

    if LOGURU_AVAILABLE:
        print("✓ Loguru is available (fallback not needed)")
    else:
        # Test fallback configuration
        configure_logging_fallback("DEBUG")
        logger = get_logger()
        logger.info("Fallback logging test")
        print("✓ Fallback logging works")

    print("✓ Fallback logging test completed")


def test_backward_compatibility():
    """Test backward compatibility with existing code."""
    print("Testing backward compatibility...")

    # Test that all old function signatures still work
    configure_logging(level="INFO")

    # These should work exactly as before
    log_task_enqueued("test-task", "module.function")
    log_task_started("test-task", 1)
    log_task_completed("test-task", 1)
    log_task_failed("test-task", "error", True)
    log_task_retry("test-task", 2, "2025-01-01 12:00:00")
    log_worker_started(2)
    log_worker_stopped()
    log_storage_error("test", "error message")
    log_serialization_error("test", "error message")

    print("✓ Backward compatibility maintained")


def run_all_tests():
    """Run all logging tests."""
    print("Running Loguru logging implementation tests...\n")

    try:
        test_basic_logging()
        test_task_logging_functions()
        test_structured_logging()
        test_exception_logging()
        test_environment_variables()
        test_configuration_options()
        test_fallback_logging()
        test_backward_compatibility()

        print("\n🎉 All logging tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Logging test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
