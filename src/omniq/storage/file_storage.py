import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import obstore as obs
from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.storage.base import BaseTaskStorage, BaseResultStorage
from omniq.serialization.manager import SerializationManager


class FileTaskStorage(BaseTaskStorage):
    """File-based storage for tasks using obstore for local and cloud storage."""

    def __init__(self, base_path: str = "tasks", cloud_config: Optional[Dict[str, Any]] = None, local_path: Optional[str] = None):
        """Initialize file storage with a base path, cloud configuration, or local path."""
        self.base_path = base_path
        self.cloud_config = cloud_config or {}
        self.local_path = local_path or os.environ.get("OMNIQ_OBSTORE_URI", "").replace("file://", "")
        # Initialize obstore store based on configuration
        if self.cloud_config:
            # Assuming cloud_config contains necessary parameters for S3 or other cloud storage
            try:
                self.store = obs.store.S3Store(
                    bucket=self.cloud_config.get("bucket", ""),
                    region=self.cloud_config.get("region", "us-east-1"),
                    skip_signature=self.cloud_config.get("skip_signature", False),
                    access_key_id=self.cloud_config.get("access_key_id", ""),
                    secret_access_key=self.cloud_config.get("secret_access_key", "")
                )
            except Exception:
                # Fallback to memory store if cloud config fails
                self.store = obs.store.MemoryStore()
        elif self.local_path:
            # Use local file storage if a local path is provided
            try:
                # Fallback to a basic memory store since specific local storage methods are not available
                self.store = obs.store.LocalStore(prefix=self.local_path)
            except Exception:
                # Fallback to memory store if local storage initialization fails
                self.store = obs.store.MemoryStore()
        else:
            self.store = obs.store.MemoryStore()
        self.serializer = SerializationManager()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the base directory exists if using local storage."""
        if self.local_path and not isinstance(self.store, obs.store.MemoryStore):
            full_path = os.path.join(self.local_path, self.base_path)
            os.makedirs(full_path, exist_ok=True)

    def _task_path(self, task_id: str) -> str:
        """Generate the file path for a task."""
        return f"{self.base_path}/{task_id}.task"

    def store_task(self, task: Task) -> None:
        """Synchronously store a task in the backend."""
        serialized = self.serializer.serialize(task)
        # Ensure serialized data is in bytes
        if isinstance(serialized, dict):
            serialized = json.dumps(serialized).encode('utf-8')
        elif not isinstance(serialized, bytes):
            serialized = str(serialized).encode('utf-8')
        obs.put(self.store, self._task_path(task.id), serialized)

    async def store_task_async(self, task: Task) -> None:
        """Asynchronously store a task in the backend."""
        serialized = self.serializer.serialize(task)
        # Ensure serialized data is in bytes
        if isinstance(serialized, dict):
            serialized = json.dumps(serialized).encode('utf-8')
        elif not isinstance(serialized, bytes):
            serialized = str(serialized).encode('utf-8')
        await obs.put_async(self.store, self._task_path(task.id), serialized)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Synchronously retrieve a task by ID."""
        try:
            response = obs.get(self.store, self._task_path(task_id))
            data = response.bytes()
            # Handle deserialization ensuring only dict is passed to deserialize
            deserialized_data = {}
            if isinstance(data, bytes):
                try:
                    potential_dict = json.loads(data.decode('utf-8'))
                    if isinstance(potential_dict, dict):
                        deserialized_data = potential_dict
                except (ValueError, UnicodeDecodeError):
                    pass
            return self.serializer.deserialize(deserialized_data, Task)
        except Exception:
            return None

    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Asynchronously retrieve a task by ID."""
        try:
            response = await obs.get_async(self.store, self._task_path(task_id))
            data = await response.bytes_async()
            # Handle deserialization ensuring only dict is passed to deserialize
            deserialized_data = {}
            if isinstance(data, bytes):
                try:
                    potential_dict = json.loads(data.decode('utf-8'))
                    if isinstance(potential_dict, dict):
                        deserialized_data = potential_dict
                except (ValueError, UnicodeDecodeError):
                    pass
            return self.serializer.deserialize(deserialized_data, Task)
        except Exception:
            return None

    def get_tasks(self, limit: int = 100) -> List[Task]:
        """Synchronously retrieve a list of tasks, optionally limited."""
        tasks = []
        try:
            list_stream = obs.list(self.store, prefix=self.base_path)
            for batch in list_stream:
                for meta in batch[:limit - len(tasks)]:
                    response = obs.get(self.store, meta.path)
                    data = response.bytes()
                    # Handle deserialization ensuring only dict is passed to deserialize
                    deserialized_data = {}
                    if isinstance(data, bytes):
                        try:
                            potential_dict = json.loads(data.decode('utf-8'))
                            if isinstance(potential_dict, dict):
                                deserialized_data = potential_dict
                        except (ValueError, UnicodeDecodeError):
                            pass
                    task = self.serializer.deserialize(deserialized_data, Task)
                    tasks.append(task)
                if len(tasks) >= limit:
                    break
        except Exception:
            pass
        return tasks

    async def get_tasks_async(self, limit: int = 100) -> List[Task]:
        """Asynchronously retrieve a list of tasks, optionally limited."""
        tasks = []
        try:
            list_stream = await obs.list(self.store, prefix=self.base_path).collect_async()
            for meta in list_stream[:limit]:
                response = await obs.get_async(self.store, meta.path)
                data = await response.bytes_async()
                # Handle deserialization ensuring only dict is passed to deserialize
                deserialized_data = {}
                if isinstance(data, bytes):
                    try:
                        potential_dict = json.loads(data.decode('utf-8'))
                        if isinstance(potential_dict, dict):
                            deserialized_data = potential_dict
                    except (ValueError, UnicodeDecodeError):
                        pass
                task = self.serializer.deserialize(deserialized_data, Task)
                tasks.append(task)
        except Exception:
            pass
        return tasks

    def delete_task(self, task_id: str) -> bool:
        """Synchronously delete a task by ID."""
        try:
            obs.delete(self.store, self._task_path(task_id))
            return True
        except Exception:
            return False

    async def delete_task_async(self, task_id: str) -> bool:
        """Asynchronously delete a task by ID."""
        try:
            await obs.delete_async(self.store, self._task_path(task_id))
            return True
        except Exception:
            return False

    def cleanup_expired_tasks(self, current_time: datetime) -> int:
        """Synchronously clean up expired tasks based on TTL."""
        count = 0
        try:
            list_stream = obs.list(self.store, prefix=self.base_path)
            for batch in list_stream:
                for meta in batch:
                    response = obs.get(self.store, meta.path)
                    data = response.bytes()
                    # Handle deserialization ensuring only dict is passed to deserialize
                    deserialized_data = {}
                    if isinstance(data, bytes):
                        try:
                            potential_dict = json.loads(data.decode('utf-8'))
                            if isinstance(potential_dict, dict):
                                deserialized_data = potential_dict
                        except (ValueError, UnicodeDecodeError):
                            pass
                    task = self.serializer.deserialize(deserialized_data, Task)
                    if task.ttl is not None and hasattr(task, 'created_at') and task.created_at and isinstance(task.created_at, datetime):
                        try:
                            ttl_seconds = float(task.ttl) if isinstance(task.ttl, (int, float, str)) and str(task.ttl).replace('.', '', 1).lstrip('-').isdigit() else 0.0
                        except (ValueError, TypeError):
                            ttl_seconds = 0.0
                        # Suppress Pylance type warning as we've already checked isinstance
                        if isinstance(task.created_at, datetime):  # type: ignore
                            expiration_time = task.created_at + timedelta(seconds=ttl_seconds)
                            if expiration_time < current_time:
                                obs.delete(self.store, meta.path)
                                count += 1
                    else:
                        # Do not delete if created_at is not datetime
                        pass
        except Exception:
            pass
        return count

    async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired tasks based on TTL."""
        count = 0
        try:
            list_stream = await obs.list(self.store, prefix=self.base_path).collect_async()
            for meta in list_stream:
                response = await obs.get_async(self.store, meta.path)
                data = await response.bytes_async()
                # Handle deserialization ensuring only dict is passed to deserialize
                deserialized_data = {}
                if isinstance(data, bytes):
                    try:
                        potential_dict = json.loads(data.decode('utf-8'))
                        if isinstance(potential_dict, dict):
                            deserialized_data = potential_dict
                    except (ValueError, UnicodeDecodeError):
                        pass
                task = self.serializer.deserialize(deserialized_data, Task)
                if task.ttl is not None and hasattr(task, 'created_at') and task.created_at and isinstance(task.created_at, datetime):
                    try:
                        ttl_seconds = float(task.ttl) if isinstance(task.ttl, (int, float, str)) and str(task.ttl).replace('.', '', 1).lstrip('-').isdigit() else 0.0
                    except (ValueError, TypeError):
                        ttl_seconds = 0.0
                    # Suppress Pylance type warning as we've already checked isinstance
                    if isinstance(task.created_at, datetime):  # type: ignore
                        expiration_time = task.created_at + timedelta(seconds=ttl_seconds)
                        if expiration_time < current_time:
                            await obs.delete_async(self.store, meta.path)
                            count += 1
                else:
                    # Do not delete if created_at is not datetime
                    pass
        except Exception:
            pass
        return count

    def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
        """Synchronously update the state of a schedule (active/paused)."""
        # Implementation for schedule state storage can be added as needed
        return False

    async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
        """Asynchronously update the state of a schedule (active/paused)."""
        # Implementation for schedule state storage can be added as needed
        return False

    def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
        """Synchronously retrieve the state of a schedule (active/paused)."""
        # Implementation for schedule state storage can be added as needed
        return None

    async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
        """Asynchronously retrieve the state of a schedule (active/paused)."""
        # Implementation for schedule state storage can be added as needed
        return None


class FileResultStorage(BaseResultStorage):
    """File-based storage for task results using obstore for local and cloud storage."""

    def __init__(self, base_path: str = "results", cloud_config: Optional[Dict[str, Any]] = None, local_path: Optional[str] = None):
        """Initialize file storage with a base path, cloud configuration, or local path."""
        self.base_path = base_path
        self.cloud_config = cloud_config or {}
        self.local_path = local_path or os.environ.get("OMNIQ_OBSTORE_URI", "").replace("file://", "")
        # Initialize obstore store based on configuration
        if self.cloud_config:
            # Assuming cloud_config contains necessary parameters for S3 or other cloud storage
            try:
                self.store = obs.store.S3Store(
                    bucket=self.cloud_config.get("bucket", ""),
                    region=self.cloud_config.get("region", "us-east-1"),
                    skip_signature=self.cloud_config.get("skip_signature", False),
                    access_key_id=self.cloud_config.get("access_key_id", ""),
                    secret_access_key=self.cloud_config.get("secret_access_key", "")
                )
            except Exception:
                # Fallback to memory store if cloud config fails
                self.store = obs.store.MemoryStore()
        elif self.local_path:
            # Use local file storage if a local path is provided
            try:
                # Fallback to a basic memory store since specific local storage methods are not available
                self.store = obs.store.LocalStore()
            except Exception:
                # Fallback to memory store if local storage initialization fails
                self.store = obs.store.MemoryStore()
        else:
            self.store = obs.store.MemoryStore()
        self.serializer = SerializationManager()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the base directory exists if using local storage."""
        if self.local_path and not isinstance(self.store, obs.store.MemoryStore):
            full_path = os.path.join(self.local_path, self.base_path)
            os.makedirs(full_path, exist_ok=True)

    def _result_path(self, task_id: str) -> str:
        """Generate the file path for a task result."""
        return f"{self.base_path}/{task_id}.result"

    def store_result(self, result: TaskResult) -> None:
        """Synchronously store a task result in the backend."""
        serialized = self.serializer.serialize(result)
        # Ensure serialized data is in bytes
        if isinstance(serialized, dict):
            serialized = json.dumps(serialized).encode('utf-8')
        elif not isinstance(serialized, bytes):
            serialized = str(serialized).encode('utf-8')
        obs.put(self.store, self._result_path(result.task_id), serialized)

    async def store_result_async(self, result: TaskResult) -> None:
        """Asynchronously store a task result in the backend."""
        serialized = self.serializer.serialize(result)
        # Ensure serialized data is in bytes
        if isinstance(serialized, dict):
            serialized = json.dumps(serialized).encode('utf-8')
        elif not isinstance(serialized, bytes):
            serialized = str(serialized).encode('utf-8')
        await obs.put_async(self.store, self._result_path(result.task_id), serialized)

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Synchronously retrieve a task result by task ID."""
        try:
            response = obs.get(self.store, self._result_path(task_id))
            data = response.bytes()
            # Handle deserialization ensuring only dict is passed to deserialize
            deserialized_data = {}
            if isinstance(data, bytes):
                try:
                    potential_dict = json.loads(data.decode('utf-8'))
                    if isinstance(potential_dict, dict):
                        deserialized_data = potential_dict
                except (ValueError, UnicodeDecodeError):
                    pass
            return self.serializer.deserialize(deserialized_data, TaskResult)
        except Exception:
            return None

    async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
        """Asynchronously retrieve a task result by task ID."""
        try:
            response = await obs.get_async(self.store, self._result_path(task_id))
            data = await response.bytes_async()
            # Handle deserialization ensuring only dict is passed to deserialize
            deserialized_data = {}
            if isinstance(data, bytes):
                try:
                    potential_dict = json.loads(data.decode('utf-8'))
                    if isinstance(potential_dict, dict):
                        deserialized_data = potential_dict
                except (ValueError, UnicodeDecodeError):
                    pass
            return self.serializer.deserialize(deserialized_data, TaskResult)
        except Exception:
            return None

    def get_results(self, limit: int = 100) -> List[TaskResult]:
        """Synchronously retrieve a list of task results, optionally limited."""
        results = []
        try:
            list_stream = obs.list(self.store, prefix=self.base_path)
            for batch in list_stream:
                for meta in batch[:limit - len(results)]:
                    response = obs.get(self.store, meta.path)
                    data = response.bytes()
                    # Handle deserialization ensuring only dict is passed to deserialize
                    deserialized_data = {}
                    if isinstance(data, bytes):
                        try:
                            potential_dict = json.loads(data.decode('utf-8'))
                            if isinstance(potential_dict, dict):
                                deserialized_data = potential_dict
                        except (ValueError, UnicodeDecodeError):
                            pass
                    result = self.serializer.deserialize(deserialized_data, TaskResult)
                    results.append(result)
                if len(results) >= limit:
                    break
        except Exception:
            pass
        return results

    async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
        """Asynchronously retrieve a list of task results, optionally limited."""
        results = []
        try:
            list_stream = await obs.list(self.store, prefix=self.base_path).collect_async()
            for meta in list_stream[:limit]:
                response = await obs.get_async(self.store, meta.path)
                data = await response.bytes_async()
                # Handle deserialization ensuring only dict is passed to deserialize
                deserialized_data = {}
                if isinstance(data, bytes):
                    try:
                        potential_dict = json.loads(data.decode('utf-8'))
                        if isinstance(potential_dict, dict):
                            deserialized_data = potential_dict
                    except (ValueError, UnicodeDecodeError):
                        pass
                result = self.serializer.deserialize(deserialized_data, TaskResult)
                results.append(result)
        except Exception:
            pass
        return results

    def delete_result(self, task_id: str) -> bool:
        """Synchronously delete a task result by task ID."""
        try:
            obs.delete(self.store, self._result_path(task_id))
            return True
        except Exception:
            return False

    async def delete_result_async(self, task_id: str) -> bool:
        """Asynchronously delete a task result by task ID."""
        try:
            await obs.delete_async(self.store, self._result_path(task_id))
            return True
        except Exception:
            return False

    def cleanup_expired_results(self, current_time: datetime) -> int:
        """Synchronously clean up expired results based on TTL."""
        count = 0
        try:
            list_stream = obs.list(self.store, prefix=self.base_path)
            for batch in list_stream:
                for meta in batch:
                    response = obs.get(self.store, meta.path)
                    data = response.bytes()
                    # Handle deserialization ensuring only dict is passed to deserialize
                    deserialized_data = {}
                    if isinstance(data, bytes):
                        try:
                            potential_dict = json.loads(data.decode('utf-8'))
                            if isinstance(potential_dict, dict):
                                deserialized_data = potential_dict
                        except (ValueError, UnicodeDecodeError):
                            pass
                    result = self.serializer.deserialize(deserialized_data, TaskResult)
                    if result.ttl is not None and hasattr(result, 'completed_at') and result.completed_at and isinstance(result.completed_at, datetime):
                        try:
                            ttl_seconds = float(result.ttl) if isinstance(result.ttl, (int, float, str)) and str(result.ttl).replace('.', '', 1).lstrip('-').isdigit() else 0.0
                        except (ValueError, TypeError):
                            ttl_seconds = 0.0
                        # Suppress Pylance type warning as we've already checked isinstance
                        if isinstance(result.completed_at, datetime):  # type: ignore
                            expiration_time = result.completed_at + timedelta(seconds=ttl_seconds)
                            if expiration_time < current_time:
                                obs.delete(self.store, meta.path)
                                count += 1
        except Exception:
            pass
        return count

    async def cleanup_expired_results_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired results based on TTL."""
        count = 0
        try:
            list_stream = await obs.list(self.store, prefix=self.base_path).collect_async()
            for meta in list_stream:
                response = await obs.get_async(self.store, meta.path)
                data = await response.bytes_async()
                # Handle deserialization ensuring only dict is passed to deserialize
                deserialized_data = {}
                if isinstance(data, bytes):
                    try:
                        potential_dict = json.loads(data.decode('utf-8'))
                        if isinstance(potential_dict, dict):
                            deserialized_data = potential_dict
                    except (ValueError, UnicodeDecodeError):
                        pass
                result = self.serializer.deserialize(deserialized_data, TaskResult)
                if result.ttl is not None and hasattr(result, 'completed_at') and result.completed_at and isinstance(result.completed_at, datetime):
                    try:
                        ttl_seconds = float(result.ttl) if isinstance(result.ttl, (int, float, str)) and str(result.ttl).replace('.', '', 1).lstrip('-').isdigit() else 0.0
                    except (ValueError, TypeError):
                        ttl_seconds = 0.0
                    # Suppress Pylance type warning as we've already checked isinstance
                    if isinstance(result.completed_at, datetime):  # type: ignore
                        expiration_time = result.completed_at + timedelta(seconds=ttl_seconds)
                        if expiration_time < current_time:
                            await obs.delete_async(self.store, meta.path)
                            count += 1
        except Exception:
            pass
        return count
