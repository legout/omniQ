#!/usr/bin/env python3
"""
Test worker compatibility fix for backward compatibility.

This test verifies that AsyncWorkerPool supports both the new queue interface
and the legacy storage interface with proper deprecation warnings.
"""

import asyncio
import warnings
from unittest.mock import Mock, AsyncMock

from src.omniq.worker import AsyncWorkerPool, WorkerPool
from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.file import FileStorage
from src.omniq.core import AsyncOmniQ, OmniQ
from src.omniq.config import Settings, BackendType
from src.omniq.serialization import JSONSerializer
import tempfile
import os


def test_worker_new_interface():
    """Test AsyncWorkerPool with new queue interface."""
    print("Testing AsyncWorkerPool with new queue interface...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage=storage)
        worker = AsyncWorkerPool(queue=queue, concurrency=4)

        assert worker.queue == queue
        assert worker.concurrency == 4
        print("✓ New interface works correctly")


def test_worker_legacy_interface():
    """Test AsyncWorkerPool with legacy storage interface."""
    print("Testing AsyncWorkerPool with legacy storage interface...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            worker = AsyncWorkerPool(storage=storage, concurrency=4)

            # Should create queue internally
            assert isinstance(worker.queue, AsyncTaskQueue)
            assert worker.queue.storage == storage
            assert worker.concurrency == 4

        # Check warning message
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
        assert "queue" in str(w[0].message)
        print("✓ Legacy interface works with deprecation warning")


def test_worker_both_parameters_error():
    """Test error when both queue and storage provided."""
    print("Testing error when both parameters provided...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage=storage)

        try:
            AsyncWorkerPool(queue=queue, storage=storage)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Cannot provide both" in str(e)
            print("✓ Correctly rejects both parameters")


def test_worker_no_parameters_error():
    """Test error when neither queue nor storage provided."""
    print("Testing error when no parameters provided...")
    try:
        AsyncWorkerPool()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Either 'queue' or 'storage'" in str(e)
        print("✓ Correctly rejects no parameters")


def test_worker_invalid_queue_type():
    """Test error for invalid queue type."""
    print("Testing error for invalid queue type...")
    try:
        AsyncWorkerPool(queue="invalid")
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "'queue' must be AsyncTaskQueue" in str(e)
        print("✓ Correctly rejects invalid queue type")


def test_worker_invalid_storage_type():
    """Test error for invalid storage type."""
    print("Testing error for invalid storage type...")
    try:
        AsyncWorkerPool(storage="invalid")
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "'storage' must be BaseStorage" in str(e)
        print("✓ Correctly rejects invalid storage type")


def test_worker_pool_new_interface():
    """Test WorkerPool with new queue interface."""
    print("Testing WorkerPool with new queue interface...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage=storage)
        worker = WorkerPool(queue=queue, concurrency=4)

        assert worker.queue == queue
        assert worker.concurrency == 4
        print("✓ WorkerPool new interface works correctly")


def test_worker_pool_legacy_interface():
    """Test WorkerPool with legacy storage interface."""
    print("Testing WorkerPool with legacy storage interface...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            worker = WorkerPool(storage=storage, concurrency=4)

            # Should create queue internally
            assert isinstance(worker.queue, AsyncTaskQueue)
            assert worker.queue.storage == storage
            assert worker.concurrency == 4

        # Check warning message
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
        assert "queue" in str(w[0].message)
        print("✓ WorkerPool legacy interface works with deprecation warning")


def test_worker_pool_both_parameters_error():
    """Test error when both queue and storage provided to WorkerPool."""
    print("Testing WorkerPool error when both parameters provided...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage=storage)

        try:
            WorkerPool(queue=queue, storage=storage)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Cannot provide both" in str(e)
            print("✓ WorkerPool correctly rejects both parameters")


def test_worker_pool_no_parameters_error():
    """Test error when neither queue nor storage provided to WorkerPool."""
    print("Testing WorkerPool error when no parameters provided...")
    try:
        WorkerPool()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Either 'queue' or 'storage'" in str(e)
        print("✓ WorkerPool correctly rejects no parameters")


async def test_async_omniq_integration():
    """Test AsyncOmniQ integration with new worker interface."""
    print("Testing AsyncOmniQ integration...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock settings that uses file backend
        settings = Settings(backend=BackendType.FILE, base_dir=temp_dir)

        omniq = AsyncOmniQ(settings=settings)

        # Should work with new internal structure
        worker = omniq.worker(concurrency=2)

        assert isinstance(worker, AsyncWorkerPool)
        assert worker.queue == omniq._queue
        assert worker.concurrency == 2
        print("✓ AsyncOmniQ integration works correctly")


def test_sync_omniq_integration():
    """Test OmniQ integration with new worker interface."""
    print("Testing OmniQ integration...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock settings that uses file backend
        settings = Settings(backend=BackendType.FILE, base_dir=temp_dir)

        omniq = OmniQ(settings=settings)

        # Should work with new internal structure
        worker = omniq.worker(concurrency=2)

        assert isinstance(worker, WorkerPool)
        assert worker.queue == omniq._async_omniq._queue
        assert worker.concurrency == 2
        print("✓ OmniQ integration works correctly")


def test_worker_logger_parameter():
    """Test AsyncWorkerPool with custom logger."""
    print("Testing AsyncWorkerPool with custom logger...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage=storage)
        custom_logger = Mock()

        worker = AsyncWorkerPool(queue=queue, logger=custom_logger)

        assert worker.logger == custom_logger
        print("✓ Custom logger works correctly")


def test_worker_legacy_with_logger():
    """Test AsyncWorkerPool legacy interface with custom logger."""
    print("Testing AsyncWorkerPool legacy interface with custom logger...")
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        custom_logger = Mock()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            worker = AsyncWorkerPool(storage=storage, logger=custom_logger)

            assert worker.logger == custom_logger
            assert isinstance(worker.queue, AsyncTaskQueue)
            assert worker.queue.storage == storage

        assert len(w) == 1
        print("✓ Legacy interface with logger works correctly")


if __name__ == "__main__":
    # Run basic tests
    test_worker_new_interface()
    test_worker_legacy_interface()
    test_worker_both_parameters_error()
    test_worker_no_parameters_error()
    test_worker_invalid_queue_type()
    test_worker_invalid_storage_type()
    test_worker_pool_new_interface()
    test_worker_pool_legacy_interface()
    test_worker_pool_both_parameters_error()
    test_worker_pool_no_parameters_error()
    test_worker_logger_parameter()
    test_worker_legacy_with_logger()

    # Run async tests
    asyncio.run(test_async_omniq_integration())
    test_sync_omniq_integration()

    print("All tests passed!")
