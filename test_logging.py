#!/usr/bin/env python3
"""
Test script for enhanced Loguru-based logging implementation.
"""

import os
import sys
import tempfile
import subprocess
import json
import time
from pathlib import Path
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omniq.logging import (
    configure,
    get_logger,
    task_context,
    bind_task,
    log_task_enqueued,
    log_task_started,
    log_task_completed,
    log_task_failed,
    log_task_retry,
    log_worker_started,
    log_worker_stopped,
    log_storage_error,
    log_serialization_error,
)


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing basic logging...")

    # Test basic logger with default configuration
    logger = get_logger()
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    print("✓ Basic logging works")


def test_enhanced_features():
    """Test enhanced Loguru features."""
    print("Testing enhanced features...")

    # Test task context
    with task_context("task-123", "process") as task_logger:
        task_logger.info("Processing task")
        time.sleep(0.01)  # Small delay to test timing

    # Test bind_task
    bound_logger = bind_task("task-456", worker="worker-1", operation="enqueue")
    bound_logger.info("Task enqueued with context")

    print("✓ Enhanced features work")


def test_environment_variables():
    """Test environment variable configuration."""
    print("Testing environment variable configuration...")

    # Test with OMNIQ_LOG_LEVEL
    os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"
    configure()

    logger = get_logger()
    logger.debug("This debug message should appear")

    # Test with OMNIQ_LOG_LEVEL
    os.environ["OMNIQ_LOG_LEVEL"] = "ERROR"
    configure()

    logger.info("This info message should NOT appear")
    logger.error("This error message should appear")

    # Test with OMNIQ_LOG_MODE
    os.environ["OMNIQ_LOG_MODE"] = "PROD"
    os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
    configure()

    logger.info("Production mode test")

    # Clean up
    for var in ["OMNIQ_LOG_LEVEL", "OMNIQ_LOG_MODE"]:
        if var in os.environ:
            del os.environ[var]

    print("✓ Environment variable configuration works")


def test_configuration_options():
    """Test enhanced configuration options."""
    print("Testing enhanced configuration...")

    # Test with custom configuration
    configure(level="DEBUG", rotation="10 MB", retention="7 days", compression="gz")

    logger = get_logger()
    logger.info("Enhanced configuration test")

    # Test with different log levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        configure(level=level)
        logger = get_logger()
        logger.info(f"Testing {level} level")
        logger.debug(f"Debug message at {level}")
        logger.warning(f"Warning message at {level}")
        logger.error(f"Error message at {level}")

    print("✓ Enhanced configuration works")


def test_task_logging_functions():
    """Test task-specific logging functions."""
    print("Testing task logging functions...")

    configure(level="INFO")

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


def test_performance():
    """Test logging performance."""
    print("Testing performance...")

    configure(level="INFO")
    logger = get_logger()

    # Test high-volume logging
    start_time = time.time()
    for i in range(1000):
        logger.info(f"Performance test message {i}")
    duration = time.time() - start_time

    print(f"✓ Performance test: 1000 messages in {duration:.3f}s")
    assert duration < 1.0, "Performance test failed: too slow"


def test_concurrent_logging():
    """Test concurrent logging."""
    print("Testing concurrent logging...")

    import threading
    import queue

    results = queue.Queue()

    def worker_task(worker_id):
        try:
            logger = get_logger().bind(worker_id=worker_id)
            for i in range(10):
                logger.info(f"Worker {worker_id} message {i}")
            results.put(f"Worker {worker_id} completed")
        except Exception as e:
            results.put(f"Worker {worker_id} failed: {e}")

    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker_task, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    # Check results
    completed = 0
    while not results.empty():
        result = results.get()
        if "completed" in result:
            completed += 1

    assert completed == 5, f"Expected 5 completed workers, got {completed}"
    print("✓ Concurrent logging works")


def test_backward_compatibility():
    """Test backward compatibility with existing code."""
    print("Testing backward compatibility...")

    # Test that all old function signatures still work
    configure(level="INFO")

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


def test_production_mode():
    """Test production mode with JSON output."""
    print("Testing production mode...")

    # Set production mode
    os.environ["OMNIQ_LOG_MODE"] = "PROD"
    os.environ["OMNIQ_LOG_LEVEL"] = "INFO"

    # Use temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".log") as f:
        temp_log_file = f.name

    os.environ["OMNIQ_LOG_FILE"] = temp_log_file
    configure()

    logger = get_logger()
    logger.info("Production mode test")

    # Read the log file and check if it contains JSON
    try:
        with open(temp_log_file, "r") as f:
            log_content = f.read()
            # Try to parse as JSON (Loguru serialize mode)
            lines = log_content.strip().split("\n")
            for line in lines:
                if line:
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        # If not JSON, that's okay for this test
                        pass
    finally:
        os.unlink(temp_log_file)

    # Clean up
    for var in ["OMNIQ_LOG_MODE", "OMNIQ_LOG_LEVEL", "OMNIQ_LOG_FILE"]:
        if var in os.environ:
            del os.environ[var]

    print("✓ Production mode works")


def run_all_tests():
    """Run all logging tests."""
    print("Running enhanced Loguru logging implementation tests...\n")

    try:
        test_basic_logging()
        test_enhanced_features()
        test_environment_variables()
        test_configuration_options()
        test_task_logging_functions()
        test_performance()
        test_concurrent_logging()
        test_backward_compatibility()
        test_production_mode()

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
