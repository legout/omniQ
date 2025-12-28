"""
Shared test fixtures and utilities for OmniQ tests.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest

from omniq.storage.base import BaseStorage
from omniq.storage.file import FileStorage
from omniq.storage.sqlite import SQLiteStorage
from omniq.queue import AsyncTaskQueue
from omniq.worker import AsyncWorkerPool
from omniq.serialization import JSONSerializer


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
async def sqlite_storage(temp_dir: str) -> AsyncGenerator[SQLiteStorage, None]:
    """Create an SQLite storage backend for testing."""
    db_path = Path(temp_dir) / "test.db"
    storage = SQLiteStorage(db_path)
    yield storage
    await storage.close()


@pytest.fixture
async def file_storage(temp_dir: str) -> AsyncGenerator[FileStorage, None]:
    """Create a File storage backend for testing."""
    storage = FileStorage(temp_dir, JSONSerializer())
    yield storage
    await storage.close()


@pytest.fixture
def storage_backend(request) -> str:
    """Parameterize storage backend selection."""
    return request.param


@pytest.fixture
async def queue(storage: BaseStorage) -> AsyncGenerator[AsyncTaskQueue, None]:
    """Create a task queue for testing."""
    queue = AsyncTaskQueue(storage)
    yield queue
    # Note: storage cleanup handled by storage fixture


@pytest.fixture
async def worker_pool(queue: AsyncTaskQueue) -> AsyncGenerator[AsyncWorkerPool, None]:
    """Create a worker pool for testing."""
    worker = AsyncWorkerPool(queue, concurrency=2, poll_interval=0.1)
    # Start worker in background
    worker_task = asyncio.create_task(worker.start())

    yield worker

    # Stop worker and cleanup
    await worker.stop()
    try:
        await asyncio.wait_for(worker_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass
