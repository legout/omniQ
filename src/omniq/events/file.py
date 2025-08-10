"""File event storage implementations for OmniQ.

This module provides concrete file-based implementations of the event storage interface:
- AsyncFileEventStorage and FileEventStorage: Event logging storage using fsspec

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import anyio
import fsspec
from fsspec.implementations.local import LocalFileSystem
from fsspec.spec import AbstractFileSystem
from pathlib import Path

from .base import BaseEventStorage
from ..models.event import TaskEvent, TaskEventType
from .. import json


class AsyncFileEventStorage(BaseEventStorage):
    """Async file-based event storage implementation.

    Features:
    - Structured event logging as JSON files
    - Time-range queries
    - Event type filtering
    - Automatic cleanup
    - Support for local and cloud storage (S3, Azure, GCP)
    """

    def __init__(
        self,
        base_dir: str = "./omniq_data",
        storage_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the async file event storage.

        Args:
            base_dir: Base directory for event storage
            storage_options: Additional options for fsspec filesystem
        """
        self.base_dir = base_dir
        self.storage_options = storage_options or {}
        self.fs: Optional[AbstractFileSystem] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the filesystem and directories are initialized."""
        if self._initialized:
            return

        # Initialize filesystem
        if self.base_dir.startswith(("s3://", "az://", "gs://", "gcs://")):
            # Cloud storage
            protocol = self.base_dir.split("://")[0]
            self.fs = fsspec.filesystem(protocol, **self.storage_options)
        else:
            # Local storage with DirFileSystem
            local_fs = LocalFileSystem(**self.storage_options)
            self.fs = fsspec.implementations.dirfs.DirFileSystem(
                fs=local_fs, path=self.base_dir
            )

        # Ensure events directory exists
        self.fs.makedirs("events", exist_ok=True)

        self._initialized = True

    def _get_task_events_dir(self, task_id: uuid.UUID) -> str:
        """Get the directory path for a task's events."""
        return f"events/{task_id}"

    def _get_event_path(self, task_id: uuid.UUID, event_timestamp: datetime) -> str:
        """Get the path for a specific event."""
        # Use timestamp with microseconds for unique filenames
        timestamp_str = event_timestamp.strftime("%Y%m%d_%H%M%S_%f")
        return f"events/{task_id}/{timestamp_str}.json"

    async def log_event_async(self, event: TaskEvent) -> None:
        """Log a task event asynchronously."""
        await self._ensure_initialized()

        task_events_dir = self._get_task_events_dir(event.task_id)
        event_path = self._get_event_path(event.task_id, event.timestamp)

        # Ensure task events directory exists
        self.fs.makedirs(task_events_dir, exist_ok=True)

        # Serialize event data
        event_data = {
            "task_id": str(event.task_id),
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "worker_id": event.worker_id,
        }

        # Write event file
        with self.fs.open(event_path, "w") as f:
            json.dump(event_data, f)

    async def get_events_async(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Get all events for a task asynchronously."""
        await self._ensure_initialized()

        task_events_dir = self._get_task_events_dir(task_id)
        events = []

        try:
            # Get all event files for the task
            event_files = self.fs.glob(f"{task_events_dir}/*.json")

            # Sort by timestamp (oldest first)
            event_files.sort(key=lambda f: self.fs.info(f)["created"])

            for event_file in event_files:
                try:
                    with self.fs.open(event_file, "r") as f:
                        event_data = json.load(f)

                    events.append(
                        TaskEvent(
                            task_id=task_id,
                            event_type=TaskEventType(event_data["event_type"]),
                            timestamp=datetime.fromisoformat(event_data["timestamp"]),
                            worker_id=event_data.get("worker_id"),
                        )
                    )
                except Exception:
                    # Skip corrupted event files
                    continue

        except Exception:
            pass

        return events

    async def get_events_by_type_async(
        self, event_type: str, limit: Optional[int] = None
    ) -> AsyncIterator[TaskEvent]:
        """Get events by type asynchronously."""
        await self._ensure_initialized()

        count = 0

        try:
            # Get all task event directories
            task_dirs = [
                d
                for d in self.fs.ls("events", detail=False)
                if self.fs.info(d)["type"] == "directory"
            ]

            # Process each task directory
            for task_dir in task_dirs:
                if limit is not None and count >= limit:
                    break

                try:
                    # Get all event files for the task
                    event_files = self.fs.glob(f"{task_dir}/*.json")

                    # Sort by timestamp (newest first)
                    event_files.sort(
                        key=lambda f: self.fs.info(f)["created"], reverse=True
                    )

                    for event_file in event_files:
                        if limit is not None and count >= limit:
                            break

                        try:
                            with self.fs.open(event_file, "r") as f:
                                event_data = json.load(f)

                            # Check event type match
                            if event_data.get("event_type") == event_type:
                                task_id = uuid.UUID(Path(task_dir).name)

                                yield TaskEvent(
                                    task_id=task_id,
                                    event_type=TaskEventType(event_data["event_type"]),
                                    timestamp=datetime.fromisoformat(
                                        event_data["timestamp"]
                                    ),
                                    worker_id=event_data.get("worker_id"),
                                )

                                count += 1
                        except Exception:
                            # Skip corrupted event files
                            continue

                except Exception:
                    # Skip corrupted task directories
                    continue

        except Exception:
            pass

    async def get_events_in_range_async(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None,
    ) -> AsyncIterator[TaskEvent]:
        """Get events within a time range asynchronously."""
        await self._ensure_initialized()

        try:
            if task_id:
                # Single task mode
                task_dirs = [self._get_task_events_dir(task_id)]
            else:
                # All tasks mode
                task_dirs = [
                    d
                    for d in self.fs.ls("events", detail=False)
                    if self.fs.info(d)["type"] == "directory"
                ]

            # Process each task directory
            for task_dir in task_dirs:
                try:
                    # Get all event files for the task
                    event_files = self.fs.glob(f"{task_dir}/*.json")

                    # Sort by timestamp (oldest first)
                    event_files.sort(key=lambda f: self.fs.info(f)["created"])

                    for event_file in event_files:
                        try:
                            with self.fs.open(event_file, "r") as f:
                                event_data = json.load(f)

                            event_timestamp = datetime.fromisoformat(
                                event_data["timestamp"]
                            )

                            # Check if event is within time range
                            if start_time <= event_timestamp <= end_time:
                                current_task_id = uuid.UUID(Path(task_dir).name)

                                yield TaskEvent(
                                    task_id=current_task_id,
                                    event_type=TaskEventType(event_data["event_type"]),
                                    timestamp=event_timestamp,
                                    worker_id=event_data.get("worker_id"),
                                )
                        except Exception:
                            # Skip corrupted event files
                            continue

                except Exception:
                    # Skip corrupted task directories
                    continue

        except Exception:
            pass

    async def cleanup_old_events_async(self, older_than: datetime) -> int:
        """Clean up old events asynchronously."""
        await self._ensure_initialized()

        count = 0

        try:
            # Get all task event directories
            task_dirs = [
                d
                for d in self.fs.ls("events", detail=False)
                if self.fs.info(d)["type"] == "directory"
            ]

            # Process each task directory
            for task_dir in task_dirs:
                try:
                    # Get all event files for the task
                    event_files = self.fs.glob(f"{task_dir}/*.json")

                    for event_file in event_files:
                        try:
                            # Check file creation time
                            file_info = self.fs.info(event_file)
                            created_time = datetime.fromtimestamp(file_info["created"])

                            if created_time < older_than:
                                self.fs.rm(event_file)
                                count += 1
                        except Exception:
                            # Skip files that can't be processed
                            continue

                    # Remove empty task directories
                    try:
                        remaining_files = self.fs.ls(task_dir, detail=False)
                        if not remaining_files:
                            self.fs.rmdir(task_dir)
                    except Exception:
                        pass

                except Exception:
                    # Skip corrupted task directories
                    continue

        except Exception:
            pass

        return count


class FileEventStorage(AsyncFileEventStorage):
    """Synchronous wrapper for AsyncFileEventStorage."""

    def log_event(self, event: TaskEvent) -> None:
        """Synchronous wrapper for log_event_async."""
        anyio.run(self.log_event_async, event)

    def get_events(self, task_id: uuid.UUID) -> List[TaskEvent]:
        """Synchronous wrapper for get_events_async."""
        return anyio.run(self.get_events_async, task_id)

    def get_events_by_type(
        self, event_type: str, limit: Optional[int] = None
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_by_type_async."""

        async def _collect_events():
            events = []
            async for event in self.get_events_by_type_async(event_type, limit):
                events.append(event)
            return events

        # Convert async generator to sync iterator
        events = anyio.run(_collect_events)
        return iter(events)

    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        task_id: Optional[uuid.UUID] = None,
    ) -> Iterator[TaskEvent]:
        """Synchronous wrapper for get_events_in_range_async."""

        async def _collect_events():
            events = []
            async for event in self.get_events_in_range_async(
                start_time, end_time, task_id
            ):
                events.append(event)
            return events

        # Convert async generator to sync iterator
        events = anyio.run(_collect_events)
        return iter(events)

    def cleanup_old_events(self, older_than: datetime) -> int:
        """Synchronous wrapper for cleanup_old_events_async."""
        return anyio.run(self.cleanup_old_events_async, older_than)
