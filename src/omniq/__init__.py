# src/omniq/__init__.py
"""OmniQ task queue library."""

from typing import Dict, Any, Optional, Union, Type, List

from omniq.queue.base import BaseTaskQueue
from omniq.storage.base import BaseResultStorage, BaseEventStorage
from omniq.workers.base import BaseWorker
from omniq.core import OmniQ

class TaskQueue:
    """Factory class for task queues."""
    
    @classmethod
    def from_config(cls, config):
        """Create task queue from config object."""
        queue_type = config.type
        return cls(type=queue_type, config=config.dict())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
        """Create task queue from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_config_file(cls, config_path: str):
        """Create task queue from config file."""
        from omniq.config.loader import load_yaml_config
        config = load_yaml_config(config_path)
        task_queue_config = config.get("task_queue", {})
        return cls(
            type=task_queue_config.get("type", "memory"),
            config=task_queue_config.get("config", {}),
            project_name=config.get("project_name", "omniq")
        )
    
    @classmethod
    def from_backend(cls, backend, **kwargs):
        """Create task queue from backend."""
        return backend.create_task_queue(**kwargs)
    
    def __new__(cls, type: str, config: Dict[str, Any] = None, project_name: str = None, **kwargs):
        """Create a task queue instance."""
        config = config or {}
        project_name = project_name or config.get("project_name", "omniq")
        
        if type == "file":
            from omniq.queue.file import FileTaskQueue
            return FileTaskQueue(
                project_name=project_name,
                base_dir=config.get("base_dir", "."),
                protocol=config.get("protocol", "file"),
                storage_options=config.get("storage_options", {}),
                queues=config.get("queues", ["default"]),
                **kwargs
            )
        elif type == "memory":
            from omniq.queue.memory import MemoryTaskQueue
            return MemoryTaskQueue(
                project_name=project_name,
                queues=config.get("queues", ["default"]),
                **kwargs
            )
        elif type == "sqlite":
            # Placeholder for SQLite implementation
            raise NotImplementedError("SQLite task queue not implemented yet")
        elif type == "postgres":
            # Placeholder for PostgreSQL implementation
            raise NotImplementedError("PostgreSQL task queue not implemented yet")
        elif type == "redis":
            # Placeholder for Redis implementation
            raise NotImplementedError("Redis task queue not implemented yet")
        elif type == "nats":
            # Placeholder for NATS implementation
            raise NotImplementedError("NATS task queue not implemented yet")
        else:
            raise ValueError(f"Unknown task queue type: {type}")

class ResultStore:
    """Factory class for result storage."""
    
    @classmethod
    def from_config(cls, config):
        """Create result storage from config object."""
        store_type = config.type
        return cls(type=store_type, config=config.dict())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
        """Create result storage from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_config_file(cls, config_path: str):
        """Create result storage from config file."""
        from omniq.config.loader import load_yaml_config
        config = load_yaml_config(config_path)
        result_store_config = config.get("result_store", {})
        return cls(
            type=result_store_config.get("type", "memory"),
            config=result_store_config.get("config", {}),
            project_name=config.get("project_name", "omniq")
        )
    
    @classmethod
    def from_backend(cls, backend, **kwargs):
        """Create result storage from backend."""
        return backend.create_result_store(**kwargs)
    
    def __new__(cls, type: str, config: Dict[str, Any] = None, project_name: str = None, **kwargs):
        """Create a result storage instance."""
        config = config or {}
        project_name = project_name or config.get("project_name", "omniq")
        
        if type == "file":
            from omniq.storage.file import FileResultStorage
            return FileResultStorage(
                project_name=project_name,
                base_dir=config.get("base_dir", "."),
                protocol=config.get("protocol", "file"),
                storage_options=config.get("storage_options", {}),
                **kwargs
            )
        elif type == "memory":
            from omniq.storage.memory import MemoryResultStorage
            return MemoryResultStorage(
                project_name=project_name,
                **kwargs
            )
        elif type == "sqlite":
            # Placeholder for SQLite implementation
            raise NotImplementedError("SQLite result storage not implemented yet")
        elif type == "postgres":
            # Placeholder for PostgreSQL implementation
            raise NotImplementedError("PostgreSQL result storage not implemented yet")
        elif type == "redis":
            # Placeholder for Redis implementation
            raise NotImplementedError("Redis result storage not implemented yet")
        elif type == "nats":
            # Placeholder for NATS implementation
            raise NotImplementedError("NATS result storage not implemented yet")
        else:
            raise ValueError(f"Unknown result storage type: {type}")

class EventStore:
    """Factory class for event storage."""
    
    @classmethod
    def from_config(cls, config):
        """Create event storage from config object."""
        store_type = config.type
        return cls(type=store_type, config=config.dict())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
        """Create event storage from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_config_file(cls, config_path: str):
        """Create event storage from config file."""
        from omniq.config.loader import load_yaml_config
        config = load_yaml_config(config_path)
        event_store_config = config.get("event_store", {})
        return cls(
            type=event_store_config.get("type", "file"),
            config=event_store_config.get("config", {}),
            project_name=config.get("project_name", "omniq")
        )
    
    @classmethod
    def from_backend(cls, backend, **kwargs):
        """Create event storage from backend."""
        return backend.create_event_store(**kwargs)
    
    def __new__(cls, type: str, config: Dict[str, Any] = None, project_name: str = None, **kwargs):
        """Create an event storage instance."""
        config = config or {}
        project_name = project_name or config.get("project_name", "omniq")
        
        if type == "file":
            from omniq.storage.file import FileEventStorage
            return FileEventStorage(
                project_name=project_name,
                base_dir=config.get("base_dir", "."),
                protocol=config.get("protocol", "file"),
                storage_options=config.get("storage_options", {}),
                **kwargs
            )
        elif type == "memory":
            from omniq.storage.memory import MemoryEventStorage
            return MemoryEventStorage(
                project_name=project_name,
                **kwargs
            )
        elif type == "sqlite":
            # Placeholder for SQLite implementation
            raise NotImplementedError("SQLite event storage not implemented yet")
        elif type == "postgres":
            # Placeholder for PostgreSQL implementation
            raise NotImplementedError("PostgreSQL event storage not implemented yet")
        else:
            raise ValueError(f"Unknown event storage type: {type}")

# Worker factory class remains unchanged