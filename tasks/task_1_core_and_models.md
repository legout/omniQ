# Task 1: Library Core, Models, Base Classes, Settings and Config

## Overview

This task involves implementing the foundational components of the OmniQ library, including core data models, base classes, and configuration management. All implementations will follow the "Async First, Sync Wrapped" pattern as specified in the project plan.

## Objectives

1. Implement core data models using msgspec.Struct for high-performance serialization
2. Create base classes for all major components following the async-first pattern
3. Implement configuration management with environment variable support
4. Establish the core OmniQ class with both async and sync interfaces
5. Implement serialization layer with intelligent format selection

## Detailed Implementation Plan

### 1.1 Core Models (`src/omniq/models/`)

#### 1.1.1 Task Model (`task.py`)

**Purpose**: Define the task data structure with metadata, dependencies, and TTL support.

**Implementation Requirements**:
- Use `msgspec.Struct` for high-performance serialization
- Support both async and sync callable references
- Implement `__hash__` and `__eq__` for dependency tracking
- Include TTL for automatic task expiration

**Code Structure**:
```python
# src/omniq/models/task.py
import msgspec
from typing import Any, Callable, Dict, Optional, Union, List
from datetime import datetime, timedelta
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    RETRY = "retry"
    EXPIRED = "expired"

class Task(msgspec.Struct):
    """Serializable task with metadata, dependencies, callbacks, and TTL."""
    
    # Core task information
    id: str
    func: Union[Callable, str]  # Function reference or serialized path
    func_args: Dict[str, Any] = msgspec.field(default_factory=dict)
    func_kwargs: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Task metadata
    name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = msgspec.field(default_factory=list)
    priority: int = 0  # Higher number = higher priority
    
    # Scheduling and execution
    status: TaskStatus = TaskStatus.PENDING
    queue_name: str = "default"
    run_at: Optional[datetime] = None
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # TTL and expiration
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    
    # Dependencies and workflow
    depends_on: List[str] = msgspec.field(default_factory=list)  # Task IDs
    callback: Optional[Union[Callable, str]] = None
    callback_args: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Retry configuration
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: timedelta = timedelta(seconds=5)
    
    # Result configuration
    result_ttl: Optional[timedelta] = None
    store_result: bool = True
    
    def __post_init__(self):
        """Post-initialization to set expires_at based on TTL."""
        if self.ttl and not self.expires_at:
            self.expires_at = self.created_at + self.ttl
    
    def __hash__(self):
        """Hash based on task ID for dependency tracking."""
        return hash(self.id)
    
    def __eq__(self, other):
        """Equality based on task ID."""
        if not isinstance(other, Task):
            return False
        return self.id == other.id
    
    @property
    def is_expired(self) -> bool:
        """Check if task has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_ready_to_run(self) -> bool:
        """Check if task is ready to run (not expired and run_at time reached)."""
        if self.is_expired:
            return False
        if self.run_at and datetime.utcnow() < self.run_at:
            return False
        return True
```

#### 1.1.2 Schedule Model (`schedule.py`)

**Purpose**: Define timing logic for task scheduling with pause/resume capability.

**Implementation Requirements**:
- Support cron, interval, and timestamp-based scheduling
- Implement pause/resume functionality
- Use `msgspec.Struct` for serialization

**Code Structure**:
```python
# src/omniq/models/schedule.py
import msgspec
from typing import Optional, Union, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

class ScheduleType(Enum):
    CRON = "cron"
    INTERVAL = "interval"
    TIMESTAMP = "timestamp"
    ONCE = "once"

class ScheduleStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Schedule(msgspec.Struct):
    """Timing logic with pause/resume capability."""
    
    # Core schedule information
    id: str
    task_id: str
    schedule_type: ScheduleType
    
    # Schedule configuration
    cron_expression: Optional[str] = None
    interval: Optional[timedelta] = None
    run_at: Optional[datetime] = None
    max_runs: Optional[int] = None
    
    # Schedule state
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    
    # Schedule metadata
    name: Optional[str] = None
    description: Optional[str] = None
    tags: list = msgspec.field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization to calculate next run time."""
        if self.status == ScheduleStatus.ACTIVE and not self.next_run_at:
            self.calculate_next_run()
    
    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time based on schedule type."""
        from croniter import croniter
        
        now = datetime.utcnow()
        
        if self.schedule_type == ScheduleType.CRON and self.cron_expression:
            cron = croniter(self.cron_expression, now)
            self.next_run_at = cron.get_next(datetime)
        elif self.schedule_type == ScheduleType.INTERVAL and self.interval:
            base_time = self.last_run_at or now
            self.next_run_at = base_time + self.interval
        elif self.schedule_type == ScheduleType.TIMESTAMP and self.run_at:
            self.next_run_at = self.run_at
        elif self.schedule_type == ScheduleType.ONCE and self.run_at:
            self.next_run_at = self.run_at if self.run_at > now else None
        else:
            self.next_run_at = None
        
        return self.next_run_at
    
    def pause(self):
        """Pause the schedule."""
        if self.status == ScheduleStatus.ACTIVE:
            self.status = ScheduleStatus.PAUSED
            self.paused_at = datetime.utcnow()
    
    def resume(self):
        """Resume the schedule."""
        if self.status == ScheduleStatus.PAUSED:
            self.status = ScheduleStatus.ACTIVE
            self.resumed_at = datetime.utcnow()
            self.calculate_next_run()
    
    @property
    def is_ready_to_run(self) -> bool:
        """Check if schedule is ready to run."""
        if self.status != ScheduleStatus.ACTIVE:
            return False
        
        if not self.next_run_at:
            return False
        
        now = datetime.utcnow()
        if now < self.next_run_at:
            return False
        
        if self.max_runs and self.run_count >= self.max_runs:
            self.status = ScheduleStatus.EXPIRED
            return False
        
        return True
    
    def mark_run(self):
        """Mark the schedule as run and calculate next run time."""
        self.last_run_at = datetime.utcnow()
        self.run_count += 1
        self.calculate_next_run()
        
        if self.max_runs and self.run_count >= self.max_runs:
            self.status = ScheduleStatus.EXPIRED
```

#### 1.1.3 Result Model (`result.py`)

**Purpose**: Define the structure for storing task execution results.

**Implementation Requirements**:
- Support different result states (pending, running, success, error)
- Include result data and error information
- Implement TTL for automatic cleanup

**Code Structure**:
```python
# src/omniq/models/result.py
import msgspec
from typing import Any, Optional
from datetime import datetime, timedelta
from enum import Enum

class ResultStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TaskResult(msgspec.Struct):
    """Execution outcome storage."""
    
    # Core result information
    task_id: str
    status: ResultStatus = ResultStatus.PENDING
    
    # Result data
    result: Any = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Timing information
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # TTL and expiration
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    
    # Execution metadata
    execution_time: Optional[float] = None  # in seconds
    worker_id: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Post-initialization to set expires_at based on TTL."""
        if self.ttl and not self.expires_at:
            self.expires_at = self.created_at + self.ttl
    
    @property
    def is_expired(self) -> bool:
        """Check if result has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def execution_duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def mark_started(self):
        """Mark the result as started."""
        self.status = ResultStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def mark_success(self, result: Any = None):
        """Mark the result as success."""
        self.status = ResultStatus.SUCCESS
        self.result = result
        self.completed_at = datetime.utcnow()
        self.execution_time = self.execution_duration
    
    def mark_error(self, error: str, traceback: Optional[str] = None):
        """Mark the result as error."""
        self.status = ResultStatus.ERROR
        self.error = error
        self.error_traceback = traceback
        self.completed_at = datetime.utcnow()
        self.execution_time = self.execution_duration
    
    def mark_cancelled(self):
        """Mark the result as cancelled."""
        self.status = ResultStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.execution_time = self.execution_duration
    
    def mark_timeout(self):
        """Mark the result as timeout."""
        self.status = ResultStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.execution_time = self.execution_duration
```

#### 1.1.4 Event Model (`event.py`)

**Purpose**: Define the structure for task lifecycle events.

**Implementation Requirements**:
- Support different event types (ENQUEUED, EXECUTING, COMPLETE, etc.)
- Include rich metadata for monitoring and debugging
- Implement structured logging

**Code Structure**:
```python
# src/omniq/models/event.py
import msgspec
from typing import Any, Optional, Dict
from datetime import datetime
from enum import Enum

class EventType(Enum):
    ENQUEUED = "enqueued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"
    RETRY = "retry"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SCHEDULE_PAUSED = "schedule_paused"
    SCHEDULE_RESUMED = "schedule_resumed"

class TaskEvent(msgspec.Struct):
    """Event logging data model."""
    
    # Core event information
    id: str
    task_id: str
    event_type: EventType
    timestamp: datetime = msgspec.field(default_factory=datetime.utcnow)
    
    # Event metadata
    queue_name: Optional[str] = None
    worker_id: Optional[str] = None
    schedule_id: Optional[str] = None
    
    # Event data
    message: Optional[str] = None
    data: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Additional context
    execution_time: Optional[float] = None
    retry_count: Optional[int] = None
    error: Optional[str] = None
    
    # Event source
    source: str = "omniq"
    level: str = "info"  # debug, info, warning, error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "queue_name": self.queue_name,
            "worker_id": self.worker_id,
            "schedule_id": self.schedule_id,
            "message": self.message,
            "data": self.data,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count,
            "error": self.error,
            "source": self.source,
            "level": self.level
        }
```

#### 1.1.5 Configuration Model (`config.py`)

**Purpose**: Define configuration structures for type-validated settings.

**Implementation Requirements**:
- Use `msgspec.Struct` for type validation
- Support nested configuration for different components
- Include default values for all settings

**Code Structure**:
```python
# src/omniq/models/config.py
import msgspec
from typing import Optional, Dict, Any, List, Union
from datetime import timedelta

class LoggingConfig(msgspec.Struct):
    """Logging configuration."""
    level: str = "INFO"
    disable_logging: bool = False
    component_levels: Dict[str, str] = msgspec.field(default_factory=dict)

class TaskQueueConfig(msgspec.Struct):
    """Task queue configuration."""
    type: str = "memory"  # memory, file, sqlite, postgres, redis, nats
    url: Optional[str] = None
    base_dir: Optional[str] = None
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)

class ResultStorageConfig(msgspec.Struct):
    """Result storage configuration."""
    type: str = "memory"  # memory, file, sqlite, postgres, redis, nats
    url: Optional[str] = None
    base_dir: Optional[str] = None
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)

class EventStorageConfig(msgspec.Struct):
    """Event storage configuration."""
    type: str = "sqlite"  # sqlite, postgres, file
    url: Optional[str] = None
    base_dir: Optional[str] = None
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)

class WorkerConfig(msgspec.Struct):
    """Worker configuration."""
    type: str = "async"  # async, thread, process, gevent
    max_workers: int = 1
    thread_workers: int = 4
    process_workers: int = 2
    gevent_workers: int = 10
    task_timeout: Optional[float] = None

class TaskConfig(msgspec.Struct):
    """Task configuration."""
    default_ttl: Optional[timedelta] = None
    default_result_ttl: Optional[timedelta] = None
    retry_attempts: int = 3
    retry_delay: timedelta = timedelta(seconds=5)

class OmniQConfig(msgspec.Struct):
    """Main OmniQ configuration."""
    project_name: str
    logging: LoggingConfig = msgspec.field(default_factory=LoggingConfig)
    task_queue: TaskQueueConfig = msgspec.field(default_factory=TaskQueueConfig)
    result_storage: ResultStorageConfig = msgspec.field(default_factory=ResultStorageConfig)
    event_storage: EventStorageConfig = msgspec.field(default_factory=EventStorageConfig)
    worker: WorkerConfig = msgspec.field(default_factory=WorkerConfig)
    task: TaskConfig = msgspec.field(default_factory=TaskConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'OmniQConfig':
        """Create configuration from dictionary."""
        return msgspec.convert(config_dict, cls)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'OmniQConfig':
        """Create configuration from YAML file."""
        import yaml
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return msgspec.to_builtins(self)
```

### 1.2 Settings and Environment Configuration (`src/omniq/config/`)

#### 1.2.1 Settings (`settings.py`)

**Purpose**: Define library settings constants without "OMNIQ_" prefix.

**Implementation Requirements**:
- Define default settings without "OMNIQ_" prefix
- Support override by environment variables with "OMNIQ_" prefix
- Include all configuration options mentioned in the project plan

**Code Structure**:
```python
# src/omniq/config/settings.py
from datetime import timedelta
from typing import Dict, Any

# Library settings without OMNIQ_ prefix
BASE_DIR = "./omniq_data"
PROJECT_NAME = "omniq"

# Logging settings
LOG_LEVEL = "INFO"
DISABLE_LOGGING = False
COMPONENT_LOG_LEVELS: Dict[str, str] = {}

# Task queue settings
TASK_QUEUE_TYPE = "memory"
TASK_QUEUE_URL = None
FSSPEC_URI = None

# Result storage settings
RESULT_STORAGE_TYPE = "memory"
RESULT_STORAGE_URL = None

# Event storage settings
EVENT_STORAGE_TYPE = "sqlite"
EVENT_STORAGE_URL = None

# Worker settings
DEFAULT_WORKER = "async"
MAX_WORKERS = 1
THREAD_WORKERS = 4
PROCESS_WORKERS = 2
GEVENT_WORKERS = 10

# Task settings
TASK_TIMEOUT = None
TASK_TTL = None
RESULT_TTL = None
RETRY_ATTEMPTS = 3
RETRY_DELAY = timedelta(seconds=5)

# Storage options
STORAGE_OPTIONS: Dict[str, Any] = {}

# Default queues
DEFAULT_QUEUES = ["default", "high", "medium", "low"]
```

#### 1.2.2 Environment Configuration (`env.py`)

**Purpose**: Load environment variables with "OMNIQ_" prefix and override settings.

**Implementation Requirements**:
- Load environment variables with "OMNIQ_" prefix
- Convert types appropriately
- Handle JSON strings for complex values

**Code Structure**:
```python
# src/omniq/config/env.py
import os
import json
from datetime import timedelta
from typing import Any, Dict, Optional
from .settings import *

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default

def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float value from environment variable."""
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default

def get_env_timedelta(key: str, default: Optional[timedelta] = None) -> Optional[timedelta]:
    """Get timedelta value from environment variable (in seconds)."""
    try:
        seconds = float(os.environ.get(key, ""))
        return timedelta(seconds=seconds)
    except (ValueError, TypeError):
        return default

def get_env_json(key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get JSON value from environment variable."""
    try:
        value = os.environ.get(key)
        if value is None:
            return default or {}
        return json.loads(value)
    except json.JSONDecodeError:
        return default or {}

# Override settings with environment variables
base_dir = os.environ.get("OMNIQ_BASE_DIR", BASE_DIR)
project_name = os.environ.get("OMNIQ_PROJECT_NAME", PROJECT_NAME)

# Logging settings
log_level = os.environ.get("OMNIQ_LOG_LEVEL", LOG_LEVEL)
disable_logging = get_env_bool("OMNIQ_DISABLE_LOGGING", DISABLE_LOGGING)
component_log_levels = get_env_json("OMNIQ_COMPONENT_LOG_LEVELS", COMPONENT_LOG_LEVELS)

# Task queue settings
task_queue_type = os.environ.get("OMNIQ_TASK_QUEUE_TYPE", TASK_QUEUE_TYPE)
task_queue_url = os.environ.get("OMNIQ_TASK_QUEUE_URL", TASK_QUEUE_URL)
fsspec_uri = os.environ.get("OMNIQ_FSSPEC_URI", FSSPEC_URI)

# Result storage settings
result_storage_type = os.environ.get("OMNIQ_RESULT_STORAGE_TYPE", RESULT_STORAGE_TYPE)
result_storage_url = os.environ.get("OMNIQ_RESULT_STORAGE_URL", RESULT_STORAGE_URL)

# Event storage settings
event_storage_type = os.environ.get("OMNIQ_EVENT_STORAGE_TYPE", EVENT_STORAGE_TYPE)
event_storage_url = os.environ.get("OMNIQ_EVENT_STORAGE_URL", EVENT_STORAGE_URL)

# Worker settings
default_worker = os.environ.get("OMNIQ_DEFAULT_WORKER", DEFAULT_WORKER)
max_workers = get_env_int("OMNIQ_MAX_WORKERS", MAX_WORKERS)
thread_workers = get_env_int("OMNIQ_THREAD_WORKERS", THREAD_WORKERS)
process_workers = get_env_int("OMNIQ_PROCESS_WORKERS", PROCESS_WORKERS)
gevent_workers = get_env_int("OMNIQ_GEVENT_WORKERS", GEVENT_WORKERS)

# Task settings
task_timeout = get_env_float("OMNIQ_TASK_TIMEOUT", TASK_TIMEOUT)
task_ttl = get_env_timedelta("OMNIQ_TASK_TTL", TASK_TTL)
result_ttl = get_env_timedelta("OMNIQ_RESULT_TTL", RESULT_TTL)
retry_attempts = get_env_int("OMNIQ_RETRY_ATTEMPTS", RETRY_ATTEMPTS)
retry_delay = get_env_timedelta("OMNIQ_RETRY_DELAY", RETRY_DELAY)

# Storage options (JSON string)
storage_options_json = os.environ.get("OMNIQ_STORAGE_OPTIONS")
storage_options = json.loads(storage_options_json) if storage_options_json else STORAGE_OPTIONS

# Default queues (JSON string)
default_queues_json = os.environ.get("OMNIQ_DEFAULT_QUEUES")
default_queues = json.loads(default_queues_json) if default_queues_json else DEFAULT_QUEUES
```

#### 1.2.3 Configuration Loader (`loader.py`)

**Purpose**: Load and validate configuration from various sources.

**Implementation Requirements**:
- Support loading from dictionaries, YAML files, and environment variables
- Validate configuration types
- Merge configurations with proper precedence

**Code Structure**:
```python
# src/omniq/config/loader.py
import os
import yaml
from typing import Dict, Any, Optional, Union
from ..models.config import OmniQConfig
from .env import *

class ConfigLoader:
    """Configuration loader with support for multiple sources."""
    
    @staticmethod
    def load_config(
        config_dict: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        env_prefix: str = "OMNIQ_"
    ) -> OmniQConfig:
        """Load configuration from multiple sources with precedence:
        1. Direct config_dict
        2. YAML config file
        3. Environment variables
        4. Default values
        """
        # Start with default configuration
        config = OmniQConfig(project_name=project_name)
        
        # Load from YAML file if provided
        if config_path and os.path.exists(config_path):
            yaml_config = ConfigLoader._load_yaml_config(config_path)
            config = ConfigLoader._merge_configs(config, yaml_config)
        
        # Load from dictionary if provided
        if config_dict:
            dict_config = OmniQConfig.from_dict(config_dict)
            config = ConfigLoader._merge_configs(config, dict_config)
        
        # Override with environment variables
        env_config = ConfigLoader._load_env_config(env_prefix)
        config = ConfigLoader._merge_configs(config, env_config)
        
        return config
    
    @staticmethod
    def _load_yaml_config(config_path: str) -> OmniQConfig:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return OmniQConfig.from_dict(config_dict)
    
    @staticmethod
    def _load_env_config(prefix: str) -> OmniQConfig:
        """Load configuration from environment variables."""
        env_dict = {}
        
        # Map environment variables to config structure
        env_mappings = {
            f"{prefix}PROJECT_NAME": ("project_name",),
            f"{prefix}LOG_LEVEL": ("logging", "level"),
            f"{prefix}DISABLE_LOGGING": ("logging", "disable_logging"),
            f"{prefix}TASK_QUEUE_TYPE": ("task_queue", "type"),
            f"{prefix}TASK_QUEUE_URL": ("task_queue", "url"),
            f"{prefix}RESULT_STORAGE_TYPE": ("result_storage", "type"),
            f"{prefix}RESULT_STORAGE_URL": ("result_storage", "url"),
            f"{prefix}EVENT_STORAGE_TYPE": ("event_storage", "type"),
            f"{prefix}EVENT_STORAGE_URL": ("event_storage", "url"),
            f"{prefix}DEFAULT_WORKER": ("worker", "type"),
            f"{prefix}MAX_WORKERS": ("worker", "max_workers"),
            f"{prefix}THREAD_WORKERS": ("worker", "thread_workers"),
            f"{prefix}PROCESS_WORKERS": ("worker", "process_workers"),
            f"{prefix}GEVENT_WORKERS": ("worker", "gevent_workers"),
            f"{prefix}TASK_TIMEOUT": ("worker", "task_timeout"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                ConfigLoader._set_nested_value(env_dict, config_path, value)
        
        return OmniQConfig.from_dict(env_dict)
    
    @staticmethod
    def _set_nested_value(d: Dict[str, Any], path: tuple, value: Any) -> None:
        """Set a nested value in a dictionary using a path tuple."""
        for key in path[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[path[-1]] = value
    
    @staticmethod
    def _merge_configs(base: OmniQConfig, override: OmniQConfig) -> OmniQConfig:
        """Merge two configurations with override taking precedence."""
        base_dict = base.to_dict()
        override_dict = override.to_dict()
        
        # Deep merge dictionaries
        merged_dict = ConfigLoader._deep_merge(base_dict, override_dict)
        
        return OmniQConfig.from_dict(merged_dict)
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
```

### 1.3 Serialization Layer (`src/omniq/serialization/`)

#### 1.3.1 Base Serializer (`base.py`)

**Purpose**: Define the base interface for all serializers.

**Implementation Requirements**:
- Define abstract methods for serialization and deserialization
- Support both sync and async interfaces
- Include error handling

**Code Structure**:
```python
# src/omniq/serialization/base.py
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic

T = TypeVar('T')

class BaseSerializer(ABC, Generic[T]):
    """Base interface for serializers."""
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes, type_hint: type = None) -> T:
        """Deserialize bytes to an object."""
        pass
    
    @abstractmethod
    def can_serialize(self, obj: Any) -> bool:
        """Check if this serializer can handle the object."""
        pass
    
    async def serialize_async(self, obj: Any) -> bytes:
        """Async version of serialize."""
        return self.serialize(obj)
    
    async def deserialize_async(self, data: bytes, type_hint: type = None) -> T:
        """Async version of deserialize."""
        return self.deserialize(data, type_hint)
```

#### 1.3.2 Msgspec Serializer (`msgspec.py`)

**Purpose**: High-performance serialization for compatible types.

**Implementation Requirements**:
- Use msgspec for fast serialization
- Support common Python types
- Implement both sync and async interfaces

**Code Structure**:
```python
# src/omniq/serialization/msgspec.py
import msgspec
from typing import Any, Type, Union, get_origin, get_args
from .base import BaseSerializer

class MsgspecSerializer(BaseSerializer[Any]):
    """High-performance serializer using msgspec."""
    
    def __init__(self):
        # Create a generic decoder that can handle common types
        self.decoder = msgspec.json.Decoder()
        self.encoder = msgspec.json.Encoder()
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes using msgspec."""
        try:
            return self.encoder.encode(obj)
        except Exception as e:
            raise ValueError(f"Msgspec serialization failed: {e}")
    
    def deserialize(self, data: bytes, type_hint: Type = None) -> Any:
        """Deserialize bytes to an object using msgspec."""
        try:
            if type_hint:
                decoder = msgspec.json.Decoder(type_hint)
                return decoder.decode(data)
            return self.decoder.decode(data)
        except Exception as e:
            raise ValueError(f"Msgspec deserialization failed: {e}")
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if msgspec can serialize this object."""
        try:
            # Try to encode the object to see if it's supported
            self.encoder.encode(obj)
            return True
        except Exception:
            return False
    
    def is_supported_type(self, obj_type: Type) -> bool:
        """Check if the type is supported by msgspec."""
        # Basic types that msgspec supports
        supported_types = (
            int, float, str, bool, bytes, None,
            list, tuple, dict, set,
        )
        
        # Check if it's a basic type
        if obj_type in supported_types:
            return True
        
        # Check if it's a generic type (like List[int])
        origin = get_origin(obj_type)
        if origin in (list, tuple, dict, set):
            return True
        
        # Check if it's a msgspec.Struct
        try:
            return issubclass(obj_type, msgspec.Struct)
        except TypeError:
            return False
```

#### 1.3.3 Dill Serializer (`dill.py`)

**Purpose**: Fallback serializer for complex Python objects.

**Implementation Requirements**:
- Use dill for serializing complex objects
- Implement security measures for deserialization
- Support both sync and async interfaces

**Code Structure**:
```python
# src/omniq/serialization/dill.py
import dill
import pickle
from typing import Any, Type, Set
from .base import BaseSerializer

class DillSerializer(BaseSerializer[Any]):
    """Fallback serializer using dill for complex objects."""
    
    def __init__(self, restrict_modules: bool = True):
        self.restrict_modules = restrict_modules
        # Safe modules that can be deserialized
        self.safe_modules: Set[str] = {
            'builtins',
            'datetime',
            'collections',
            'decimal',
            'fractions',
            'numbers',
            'typing',
            'enum',
            'dataclasses',
            'msgspec',
        }
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes using dill."""
        try:
            return dill.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise ValueError(f"Dill serialization failed: {e}")
    
    def deserialize(self, data: bytes, type_hint: Type = None) -> Any:
        """Deserialize bytes to an object using dill."""
        try:
            obj = dill.loads(data)
            
            # Security check if restriction is enabled
            if self.restrict_modules:
                self._check_object_safety(obj)
            
            return obj
        except Exception as e:
            raise ValueError(f"Dill deserialization failed: {e}")
    
    def can_serialize(self, obj: Any) -> bool:
        """Dill can serialize almost anything, so always return True."""
        return True
    
    def _check_object_safety(self, obj: Any, visited: set = None) -> None:
        """Recursively check if an object is safe to deserialize."""
        if visited is None:
            visited = set()
        
        # Avoid infinite recursion
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)
        
        # Check module safety for objects with __module__
        if hasattr(obj, '__module__') and obj.__module__:
            module = obj.__module__.split('.')[0]
            if module not in self.safe_modules and not module.startswith('omniq'):
                raise SecurityError(f"Unsafe module in deserialized object: {module}")
        
        # Recursively check containers
        if isinstance(obj, (list, tuple, set)):
            for item in obj:
                self._check_object_safety(item, visited)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                self._check_object_safety(key, visited)
                self._check_object_safety(value, visited)

class SecurityError(Exception):
    """Raised when a potentially unsafe object is detected during deserialization."""
    pass
```

#### 1.3.4 Serialization Manager (`manager.py`)

**Purpose**: Orchestrate serialization strategy with automatic format selection.

**Implementation Requirements**:
- Automatically select the best serializer for each object
- Store serialization format with data
- Implement both sync and async interfaces

**Code Structure**:
```python
# src/omniq/serialization/manager.py
from typing import Any, Optional, Dict, Type
from .base import BaseSerializer
from .msgspec import MsgspecSerializer
from .dill import DillSerializer

class SerializationManager:
    """Orchestrates serialization strategy with automatic format selection."""
    
    def __init__(self, restrict_dill_modules: bool = True):
        self.serializers: list[BaseSerializer] = [
            MsgspecSerializer(),
            DillSerializer(restrict_modules=restrict_dill_modules)
        ]
        self.format_marker = b"OMNIQ_FORMAT:"
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object with automatic format selection."""
        # Try serializers in order of preference
        for i, serializer in enumerate(self.serializers):
            if serializer.can_serialize(obj):
                try:
                    data = serializer.serialize(obj)
                    # Prepend format marker
                    return self.format_marker + str(i).encode() + b":" + data
                except Exception:
                    continue
        
        # If all serializers fail, raise an error
        raise ValueError(f"Could not serialize object of type {type(obj)}")
    
    def deserialize(self, data: bytes, type_hint: Type = None) -> Any:
        """Deserialize data with automatic format detection."""
        # Check if data has format marker
        if not data.startswith(self.format_marker):
            # Legacy data without format marker, try msgspec first
            try:
                return self.serializers[0].deserialize(data, type_hint)
            except Exception:
                return self.serializers[1].deserialize(data, type_hint)
        
        # Extract format index and data
        marker_end = data.find(b":", len(self.format_marker))
        if marker_end == -1:
            raise ValueError("Invalid serialization format")
        
        try:
            format_index = int(data[len(self.format_marker):marker_end].decode())
            serializer_data = data[marker_end + 1:]
            
            if 0 <= format_index < len(self.serializers):
                return self.serializers[format_index].deserialize(serializer_data, type_hint)
            else:
                raise ValueError(f"Unknown serialization format: {format_index}")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to deserialize data: {e}")
    
    async def serialize_async(self, obj: Any) -> bytes:
        """Async version of serialize."""
        return self.serialize(obj)
    
    async def deserialize_async(self, data: bytes, type_hint: Type = None) -> Any:
        """Async version of deserialize."""
        return self.deserialize(data, type_hint)
    
    def get_serializer_for_object(self, obj: Any) -> Optional[BaseSerializer]:
        """Get the best serializer for a given object."""
        for serializer in self.serializers:
            if serializer.can_serialize(obj):
                return serializer
        return None
```
### 1.4 Base Classes (`src/omniq/base/`)

#### 1.4.1 Base Task Queue (`queue.py`)

**Purpose**: Define the abstract interface for all task queue implementations.

**Implementation Requirements**:
- Define abstract methods for task queue operations
- Support both sync and async interfaces
- Include context manager support

**Code Structure**:
```python
# src/omniq/base/queue.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncContextManager, ContextManager
from contextlib import asynccontextmanager, contextmanager
from ..models.task import Task, TaskStatus
from ..models.schedule import Schedule

class BaseTaskQueue(ABC):
    """Abstract interface for task queue implementations."""
    
    def __init__(self, project_name: str, queues: List[str] = None):
        self.project_name = project_name
        self.queues = queues or ["default"]
    
    @abstractmethod
    async def enqueue_async(self, task: Task) -> str:
        """Enqueue a task asynchronously."""
        pass
    
    @abstractmethod
    async def dequeue_async(self, queues: List[str] = None, timeout: float = None) -> Optional[Task]:
        """Dequeue a task asynchronously."""
        pass
    
    @abstractmethod
    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Get a task by ID asynchronously."""
        pass
    
    @abstractmethod
    async def update_task_async(self, task: Task) -> bool:
        """Update a task asynchronously."""
        pass
    
    @abstractmethod
    async def delete_task_async(self, task_id: str) -> bool:
        """Delete a task asynchronously."""
        pass
    
    @abstractmethod
    async def size_async(self, queue_name: str = None) -> int:
        """Get queue size asynchronously."""
        pass
    
    @abstractmethod
    async def clear_async(self, queue_name: str = None) -> int:
        """Clear queue asynchronously."""
        pass
    
    @abstractmethod
    async def schedule_async(self, schedule: Schedule) -> str:
        """Schedule a task asynchronously."""
        pass
    
    @abstractmethod
    async def get_schedule_async(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID asynchronously."""
        pass
    
    @abstractmethod
    async def update_schedule_async(self, schedule: Schedule) -> bool:
        """Update a schedule asynchronously."""
        pass
    
    @abstractmethod
    async def delete_schedule_async(self, schedule_id: str) -> bool:
        """Delete a schedule asynchronously."""
        pass
    
    @abstractmethod
    async def get_ready_schedules_async(self) -> List[Schedule]:
        """Get ready-to-run schedules asynchronously."""
        pass
    
    # Sync wrappers
    def enqueue(self, task: Task) -> str:
        """Enqueue a task synchronously."""
        return self._run_async(self.enqueue_async(task))
    
    def dequeue(self, queues: List[str] = None, timeout: float = None) -> Optional[Task]:
        """Dequeue a task synchronously."""
        return self._run_async(self.dequeue_async(queues, timeout))
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID synchronously."""
        return self._run_async(self.get_task_async(task_id))
    
    def update_task(self, task: Task) -> bool:
        """Update a task synchronously."""
        return self._run_async(self.update_task_async(task))
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task synchronously."""
        return self._run_async(self.delete_task_async(task_id))
    
    def size(self, queue_name: str = None) -> int:
        """Get queue size synchronously."""
        return self._run_async(self.size_async(queue_name))
    
    def clear(self, queue_name: str = None) -> int:
        """Clear queue synchronously."""
        return self._run_async(self.clear_async(queue_name))
    
    def schedule(self, schedule: Schedule) -> str:
        """Schedule a task synchronously."""
        return self._run_async(self.schedule_async(schedule))
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID synchronously."""
        return self._run_async(self.get_schedule_async(schedule_id))
    
    def update_schedule(self, schedule: Schedule) -> bool:
        """Update a schedule synchronously."""
        return self._run_async(self.update_schedule_async(schedule))
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule synchronously."""
        return self._run_async(self.delete_schedule_async(schedule_id))
    
    def get_ready_schedules(self) -> List[Schedule]:
        """Get ready-to-run schedules synchronously."""
        return self._run_async(self.get_ready_schedules_async())
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
    
    # Context managers
    @asynccontextmanager
    async def async_context(self):
        """Async context manager."""
        try:
            await self.start_async()
            yield self
        finally:
            await self.stop_async()
    
    @contextmanager
    def sync_context(self):
        """Sync context manager."""
        try:
            self.start()
            yield self
        finally:
            self.stop()
    
    # Lifecycle methods
    @abstractmethod
    async def start_async(self):
        """Start the task queue asynchronously."""
        pass
    
    @abstractmethod
    async def stop_async(self):
        """Stop the task queue asynchronously."""
        pass
    
    def start(self):
        """Start the task queue synchronously."""
        self._run_async(self.start_async())
    
    def stop(self):
        """Stop the task queue synchronously."""
        self._run_async(self.stop_async())
```

#### 1.4.2 Base Result Storage (`result_storage.py`)

**Purpose**: Define the abstract interface for all result storage implementations.

**Implementation Requirements**:
- Define abstract methods for result storage operations
- Support both sync and async interfaces
- Include context manager support

**Code Structure**:
```python
# src/omniq/base/result_storage.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncContextManager, ContextManager
from contextlib import asynccontextmanager, contextmanager
from ..models.result import TaskResult, ResultStatus

class BaseResultStorage(ABC):
    """Abstract interface for result storage implementations."""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
    
    @abstractmethod
    async def store_async(self, result: TaskResult) -> bool:
        """Store a result asynchronously."""
        pass
    
    @abstractmethod
    async def get_async(self, task_id: str) -> Optional[TaskResult]:
        """Get a result by task ID asynchronously."""
        pass
    
    @abstractmethod
    async def get_latest_async(self, schedule_id: str) -> Optional[TaskResult]:
        """Get the latest result for a schedule asynchronously."""
        pass
    
    @abstractmethod
    async def update_async(self, result: TaskResult) -> bool:
        """Update a result asynchronously."""
        pass
    
    @abstractmethod
    async def delete_async(self, task_id: str) -> bool:
        """Delete a result asynchronously."""
        pass
    
    @abstractmethod
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        pass
    
    @abstractmethod
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get storage statistics asynchronously."""
        pass
    
    # Sync wrappers
    def store(self, result: TaskResult) -> bool:
        """Store a result synchronously."""
        return self._run_async(self.store_async(result))
    
    def get(self, task_id: str) -> Optional[TaskResult]:
        """Get a result by task ID synchronously."""
        return self._run_async(self.get_async(task_id))
    
    def get_latest(self, schedule_id: str) -> Optional[TaskResult]:
        """Get the latest result for a schedule synchronously."""
        return self._run_async(self.get_latest_async(schedule_id))
    
    def update(self, result: TaskResult) -> bool:
        """Update a result synchronously."""
        return self._run_async(self.update_async(result))
    
    def delete(self, task_id: str) -> bool:
        """Delete a result synchronously."""
        return self._run_async(self.delete_async(task_id))
    
    def cleanup_expired(self) -> int:
        """Clean up expired results synchronously."""
        return self._run_async(self.cleanup_expired_async())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics synchronously."""
        return self._run_async(self.get_stats_async())
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
    
    # Context managers
    @asynccontextmanager
    async def async_context(self):
        """Async context manager."""
        try:
            await self.start_async()
            yield self
        finally:
            await self.stop_async()
    
    @contextmanager
    def sync_context(self):
        """Sync context manager."""
        try:
            self.start()
            yield self
        finally:
            self.stop()
    
    # Lifecycle methods
    @abstractmethod
    async def start_async(self):
        """Start the result storage asynchronously."""
        pass
    
    @abstractmethod
    async def stop_async(self):
        """Stop the result storage asynchronously."""
        pass
    
    def start(self):
        """Start the result storage synchronously."""
        self._run_async(self.start_async())
    
    def stop(self):
        """Stop the result storage synchronously."""
        self._run_async(self.stop_async())
```

#### 1.4.3 Base Event Storage (`event_storage.py`)

**Purpose**: Define the abstract interface for all event storage implementations.

**Implementation Requirements**:
- Define abstract methods for event storage operations
- Support both sync and async interfaces
- Include context manager support

**Code Structure**:
```python
# src/omniq/base/event_storage.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncContextManager, ContextManager
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from ..models.event import TaskEvent, EventType

class BaseEventStorage(ABC):
    """Abstract interface for event storage implementations."""
    
    def __init__(self, project_name: str):
        self.project_name = project_name
    
    @abstractmethod
    async def log_async(self, event: TaskEvent) -> bool:
        """Log an event asynchronously."""
        pass
    
    @abstractmethod
    async def get_events_async(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get events asynchronously."""
        pass
    
    @abstractmethod
    async def get_latest_events_async(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 10
    ) -> List[TaskEvent]:
        """Get latest events asynchronously."""
        pass
    
    @abstractmethod
    async def cleanup_expired_async(self) -> int:
        """Clean up expired events asynchronously."""
        pass
    
    @abstractmethod
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get storage statistics asynchronously."""
        pass
    
    # Sync wrappers
    def log(self, event: TaskEvent) -> bool:
        """Log an event synchronously."""
        return self._run_async(self.log_async(event))
    
    def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get events synchronously."""
        return self._run_async(
            self.get_events_async(task_id, event_type, start_time, end_time, limit)
        )
    
    def get_latest_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 10
    ) -> List[TaskEvent]:
        """Get latest events synchronously."""
        return self._run_async(self.get_latest_events_async(task_id, event_type, limit))
    
    def cleanup_expired(self) -> int:
        """Clean up expired events synchronously."""
        return self._run_async(self.cleanup_expired_async())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics synchronously."""
        return self._run_async(self.get_stats_async())
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
    
    # Context managers
    @asynccontextmanager
    async def async_context(self):
        """Async context manager."""
        try:
            await self.start_async()
            yield self
        finally:
            await self.stop_async()
    
    @contextmanager
    def sync_context(self):
        """Sync context manager."""
        try:
            self.start()
            yield self
        finally:
            self.stop()
    
    # Lifecycle methods
    @abstractmethod
    async def start_async(self):
        """Start the event storage asynchronously."""
        pass
    
    @abstractmethod
    async def stop_async(self):
        """Stop the event storage asynchronously."""
        pass
    
    def start(self):
        """Start the event storage synchronously."""
        self._run_async(self.start_async())
    
    def stop(self):
        """Stop the event storage synchronously."""
        self._run_async(self.stop_async())
```

#### 1.4.4 Base Worker (`worker.py`)

**Purpose**: Define the abstract interface for all worker implementations.

**Implementation Requirements**:
- Define abstract methods for worker operations
- Support both sync and async interfaces
- Include context manager support

**Code Structure**:
```python
# src/omniq/base/worker.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncContextManager, ContextManager, Callable
from contextlib import asynccontextmanager, contextmanager
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent, EventType

class BaseWorker(ABC):
    """Abstract interface for worker implementations."""
    
    def __init__(
        self,
        task_queue,
        result_storage,
        event_storage,
        worker_id: Optional[str] = None,
        **kwargs
    ):
        self.task_queue = task_queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.worker_id = worker_id or self._generate_worker_id()
        self.is_running = False
        self.task_callback: Optional[Callable] = None
    
    def _generate_worker_id(self) -> str:
        """Generate a unique worker ID."""
        import uuid
        return f"worker-{uuid.uuid4().hex[:8]}"
    
    @abstractmethod
    async def start_async(self):
        """Start the worker asynchronously."""
        pass
    
    @abstractmethod
    async def stop_async(self):
        """Stop the worker asynchronously."""
        pass
    
    @abstractmethod
    async def process_task_async(self, task: Task) -> TaskResult:
        """Process a task asynchronously."""
        pass
    
    @abstractmethod
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get worker statistics asynchronously."""
        pass
    
    # Sync wrappers
    def start(self):
        """Start the worker synchronously."""
        self._run_async(self.start_async())
    
    def stop(self):
        """Stop the worker synchronously."""
        self._run_async(self.stop_async())
    
    def process_task(self, task: Task) -> TaskResult:
        """Process a task synchronously."""
        return self._run_async(self.process_task_async(task))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics synchronously."""
        return self._run_async(self.get_stats_async())
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
    
    # Context managers
    @asynccontextmanager
    async def async_context(self):
        """Async context manager."""
        try:
            await self.start_async()
            yield self
        finally:
            await self.stop_async()
    
    @contextmanager
    def sync_context(self):
        """Sync context manager."""
        try:
            self.start()
            yield self
        finally:
            self.stop()
    
    # Task execution helpers
    async def _execute_task_async(self, task: Task) -> TaskResult:
        """Execute a task and handle result/error."""
        import traceback
        import datetime
        from ..serialization.manager import SerializationManager
        
        # Create result
        result = TaskResult(task_id=task.id)
        result.worker_id = self.worker_id
        result.retry_count = task.retry_count
        
        # Log execution start
        event = TaskEvent(
            task_id=task.id,
            event_type=EventType.EXECUTING,
            queue_name=task.queue_name,
            worker_id=self.worker_id,
            message=f"Task execution started",
            data={"retry_count": task.retry_count}
        )
        await self.event_storage.log_async(event)
        
        try:
            # Mark result as started
            result.mark_started()
            await self.result_storage.update_async(result)
            
            # Deserialize function if needed
            serialization_manager = SerializationManager()
            func = task.func
            if isinstance(func, str):
                # Function is serialized, deserialize it
                func = serialization_manager.deserialize(func.encode())
            
            # Execute the function
            import asyncio
            if asyncio.iscoroutinefunction(func):
                # Async function
                task_result = await func(**task.func_args, **task.func_kwargs)
            else:
                # Sync function
                task_result = func(**task.func_args, **task.func_kwargs)
            
            # Mark result as success
            result.mark_success(task_result)
            
            # Log completion
            event = TaskEvent(
                task_id=task.id,
                event_type=EventType.COMPLETED,
                queue_name=task.queue_name,
                worker_id=self.worker_id,
                message=f"Task completed successfully",
                data={"execution_time": result.execution_time}
            )
            await self.event_storage.log_async(event)
            
        except Exception as e:
            # Mark result as error
            error_msg = str(e)
            error_tb = traceback.format_exc()
            result.mark_error(error_msg, error_tb)
            
            # Log error
            event = TaskEvent(
                task_id=task.id,
                event_type=EventType.ERROR,
                queue_name=task.queue_name,
                worker_id=self.worker_id,
                message=f"Task execution failed: {error_msg}",
                data={"error": error_msg, "execution_time": result.execution_time},
                error=error_msg
            )
            await self.event_storage.log_async(event)
        
        # Store result
        await self.result_storage.update_async(result)
        
        # Call task callback if provided
        if self.task_callback:
            try:
                if asyncio.iscoroutinefunction(self.task_callback):
                    await self.task_callback(task, result)
                else:
                    self.task_callback(task, result)
            except Exception as e:
                # Log callback error but don't fail the task
                event = TaskEvent(
                    task_id=task.id,
                    event_type=EventType.ERROR,
                    queue_name=task.queue_name,
                    worker_id=self.worker_id,
                    message=f"Task callback failed: {str(e)}",
                    data={"callback_error": str(e)},
                    error=str(e)
                )
                await self.event_storage.log_async(event)
        
        return result
    
    def _execute_task(self, task: Task) -> TaskResult:
        """Execute a task synchronously."""
        return self._run_async(self._execute_task_async(task))
    
    def set_task_callback(self, callback: Callable):
        """Set a callback to be called after each task execution."""
        self.task_callback = callback
```

### 1.5 Core OmniQ Implementation (`src/omniq/core.py`)

**Purpose**: Implement the main OmniQ class that orchestrates all components.

**Implementation Requirements**:
- Implement both async and sync interfaces
- Support multiple configuration methods
- Include context manager support
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/core.py
import uuid
import datetime as dt
from typing import Optional, Dict, Any, List, Union, Callable
from contextlib import asynccontextmanager, contextmanager

from .models.task import Task, TaskStatus
from .models.schedule import Schedule, ScheduleType
from .models.result import TaskResult, ResultStatus
from .models.event import TaskEvent, EventType
from .models.config import OmniQConfig
from .config.loader import ConfigLoader
from .base.queue import BaseTaskQueue
from .base.result_storage import BaseResultStorage
from .base.event_storage import BaseEventStorage
from .base.worker import BaseWorker
from .serialization.manager import SerializationManager

class OmniQ:
    """Main OmniQ class that orchestrates all components."""
    
    def __init__(
        self,
        config: Optional[OmniQConfig] = None,
        task_queue: Optional[BaseTaskQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        worker: Optional[BaseWorker] = None,
        **kwargs
    ):
        # Load configuration
        if config is None:
            config = ConfigLoader.load_config()
        
        self.config = config
        
        # Initialize components
        self.task_queue = task_queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.worker = worker
        
        # Serialization manager
        self.serialization_manager = SerializationManager()
        
        # Task callback
        self.task_callback: Optional[Callable] = None
    
    @classmethod
    def from_config(cls, config: Union[OmniQConfig, Dict[str, Any]]) -> 'OmniQ':
        """Create OmniQ instance from configuration."""
        if isinstance(config, dict):
            config = OmniQConfig.from_dict(config)
        
        return cls(config=config)
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'OmniQ':
        """Create OmniQ instance from configuration file."""
        config = ConfigLoader.load_config(config_path=config_path)
        return cls(config=config)
    
    @classmethod
    def from_backend(
        cls,
        backend,
        result_store_backend=None,
        event_store_backend=None,
        worker_type: str = "async",
        worker_config: Optional[Dict[str, Any]] = None
    ) -> 'OmniQ':
        """Create OmniQ instance from backend(s)."""
        # Import here to avoid circular imports
        from .backends import get_task_queue, get_result_storage, get_event_storage, get_worker
        
        # Create components from backends
        task_queue = get_task_queue(backend)
        result_storage = get_result_storage(result_store_backend or backend)
        event_storage = get_event_storage(event_store_backend or backend)
        worker = get_worker(
            worker_type=worker_type,
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            **(worker_config or {})
        )
        
        return cls(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            worker=worker
        )
    
    # Async methods
    async def start_async(self):
        """Start all components asynchronously."""
        if self.task_queue:
            await self.task_queue.start_async()
        if self.result_storage:
            await self.result_storage.start_async()
        if self.event_storage:
            await self.event_storage.start_async()
        if self.worker:
            await self.worker.start_async()
    
    async def stop_async(self):
        """Stop all components asynchronously."""
        if self.worker:
            await self.worker.stop_async()
        if self.event_storage:
            await self.event_storage.stop_async()
        if self.result_storage:
            await self.result_storage.stop_async()
        if self.task_queue:
            await self.task_queue.stop_async()
    
    async def enqueue_async(
        self,
        func,
        func_args: Optional[Dict[str, Any]] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        run_at: Optional[dt.datetime] = None,
        run_in: Optional[dt.timedelta] = None,
        ttl: Optional[dt.timedelta] = None,
        result_ttl: Optional[dt.timedelta] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0,
        depends_on: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        callback_args: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: dt.timedelta = dt.timedelta(seconds=5),
        store_result: bool = True
    ) -> str:
        """Enqueue a task asynchronously."""
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Calculate run_at time
        if run_in and not run_at:
            run_at = dt.datetime.utcnow() + run_in
        
        # Create task
        task = Task(
            id=task_id,
            func=func,
            func_args=func_args or {},
            func_kwargs=func_kwargs or {},
            queue_name=queue_name,
            run_at=run_at,
            ttl=ttl,
            result_ttl=result_ttl,
            name=name,
            description=description,
            tags=tags or [],
            priority=priority,
            depends_on=depends_on or [],
            callback=callback,
            callback_args=callback_args or {},
            max_retries=max_retries,
            retry_delay=retry_delay,
            store_result=store_result
        )
        
        # Enqueue task
        await self.task_queue.enqueue_async(task)
        
        # Log event
        event = TaskEvent(
            task_id=task_id,
            event_type=EventType.ENQUEUED,
            queue_name=queue_name,
            message=f"Task enqueued to {queue_name} queue",
            data={"func_name": getattr(func, '__name__', str(func))}
        )
        await self.event_storage.log_async(event)
        
        return task_id
    
    async def schedule_async(
        self,
        func,
        func_args: Optional[Dict[str, Any]] = None,
        func_kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        schedule_type: ScheduleType = ScheduleType.INTERVAL,
        cron_expression: Optional[str] = None,
        interval: Optional[dt.timedelta] = None,
        run_at: Optional[dt.datetime] = None,
        max_runs: Optional[int] = None,
        ttl: Optional[dt.timedelta] = None,
        result_ttl: Optional[dt.timedelta] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0,
        depends_on: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        callback_args: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: dt.timedelta = dt.timedelta(seconds=5),
        store_result: bool = True
    ) -> str:
        """Schedule a task asynchronously."""
        # Generate schedule ID
        schedule_id = str(uuid.uuid4())
        
        # Create task first
        task_id = await self.enqueue_async(
            func=func,
            func_args=func_args,
            func_kwargs=func_kwargs,
            queue_name=queue_name,
            ttl=ttl,
            result_ttl=result_ttl,
            name=name,
            description=description,
            tags=tags,
            priority=priority,
            depends_on=depends_on,
            callback=callback,
            callback_args=callback_args,
            max_retries=max_retries,
            retry_delay=retry_delay,
            store_result=store_result
        )
        
        # Create schedule
        schedule = Schedule(
            id=schedule_id,
            task_id=task_id,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval=interval,
            run_at=run_at,
            max_runs=max_runs,
            name=name,
            description=description,
            tags=tags or []
        )
        
        # Schedule task
        await self.task_queue.schedule_async(schedule)
        
        return schedule_id
    
    async def get_result_async(
        self,
        task_id: Optional[str] = None,
        schedule_id: Optional[str] = None,
        kind: str = "latest"
    ) -> Optional[TaskResult]:
        """Get a task result asynchronously."""
        if schedule_id:
            if kind == "latest":
                return await self.result_storage.get_latest_async(schedule_id)
            else:
                raise ValueError(f"Unsupported kind for schedule_id: {kind}")
        elif task_id:
            return await self.result_storage.get_async(task_id)
        else:
            raise ValueError("Either task_id or schedule_id must be provided")
    
    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Get a task by ID asynchronously."""
        return await self.task_queue.get_task_async(task_id)
    
    async def get_schedule_async(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID asynchronously."""
        return await self.task_queue.get_schedule_async(schedule_id)
    
    async def get_events_async(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[dt.datetime] = None,
        end_time: Optional[dt.datetime] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get events asynchronously."""
        return await self.event_storage.get_events_async(
            task_id=task_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get system statistics asynchronously."""
        stats = {}
        
        if self.task_queue:
            queue_stats = {}
            for queue_name in self.task_queue.queues:
                queue_stats[queue_name] = await self.task_queue.size_async(queue_name)
            stats["queues"] = queue_stats
        
        if self.result_storage:
            stats["results"] = await self.result_storage.get_stats_async()
        
        if self.event_storage:
            stats["events"] = await self.event_storage.get_stats_async()
        
        if self.worker:
            stats["worker"] = await self.worker.get_stats_async()
        
        return stats
    
    async def cleanup_expired_async(self) -> Dict[str, int]:
        """Clean up expired tasks, results, and events asynchronously."""
        results = {}
        
        if self.result_storage:
            results["results"] = await self.result_storage.cleanup_expired_async()
        
        if self.event_storage:
            results["events"] = await self.event_storage.cleanup_expired_async()
        
        return results
    
    # Sync wrappers
    def start(self):
        """Start all components synchronously."""
        self._run_async(self.start_async())
    
    def stop(self):
        """Stop all components synchronously."""
        self._run_async(self.stop_async())
    
    def enqueue(self, *args, **kwargs) -> str:
        """Enqueue a task synchronously."""
        return self._run_async(self.enqueue_async(*args, **kwargs))
    
    def schedule(self, *args, **kwargs) -> str:
        """Schedule a task synchronously."""
        return self._run_async(self.schedule_async(*args, **kwargs))
    
    def get_result(self, *args, **kwargs) -> Optional[TaskResult]:
        """Get a task result synchronously."""
        return self._run_async(self.get_result_async(*args, **kwargs))
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID synchronously."""
        return self._run_async(self.get_task_async(task_id))
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID synchronously."""
        return self._run_async(self.get_schedule_async(schedule_id))
    
    def get_events(self, *args, **kwargs) -> List[TaskEvent]:
        """Get events synchronously."""
        return self._run_async(self.get_events_async(*args, **kwargs))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics synchronously."""
        return self._run_async(self.get_stats_async())
    
    def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired tasks, results, and events synchronously."""
        return self._run_async(self.cleanup_expired_async())
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
    
    # Context managers
    @asynccontextmanager
    async def async_context(self):
        """Async context manager."""
        try:
            await self.start_async()
            yield self
        finally:
            await self.stop_async()
    
    @contextmanager
    def sync_context(self):
        """Sync context manager."""
        try:
            self.start()
            yield self
        finally:
            self.stop()
    
    def __enter__(self):
        """Enter sync context manager."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context manager."""
        self.stop()
    
    async def __aenter__(self):
        """Enter async context manager."""
        await self.start_async()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.stop_async()
    
    # Worker management
    def start_worker(self):
        """Start the worker synchronously."""
        if self.worker:
            self.worker.start()
    
    def stop_worker(self):
        """Stop the worker synchronously."""
        if self.worker:
            self.worker.stop()
    
    async def start_worker_async(self):
        """Start the worker asynchronously."""
        if self.worker:
            await self.worker.start_async()
    
    async def stop_worker_async(self):
        """Stop the worker asynchronously."""
        if self.worker:
            await self.worker.stop_async()
    
    def set_task_callback(self, callback: Callable):
        """Set a callback to be called after each task execution."""
        self.task_callback = callback
        if self.worker:
            self.worker.set_task_callback(callback)
```

### 1.6 Package Initialization (`src/omniq/__init__.py`)

**Purpose**: Initialize the OmniQ package and expose public APIs.

**Implementation Requirements**:
- Import and expose main classes and functions
- Set up package-level configuration
- Include version information

**Code Structure**:
```python
# src/omniq/__init__.py
"""
OmniQ: A Flexible Task Queue Library for Python

OmniQ is a modular Python task queue library designed for both local and 
distributed task processing. It provides a flexible architecture that supports 
multiple storage backends, worker types, and configuration methods.
"""

__version__ = "0.1.0"
__author__ = "OmniQ Team"
__email__ = "team@omniq.dev"

# Import main classes
from .core import OmniQ
from .models.task import Task, TaskStatus
from .models.schedule import Schedule, ScheduleType
from .models.result import TaskResult, ResultStatus
from .models.event import TaskEvent, EventType
from .models.config import OmniQConfig

# Import base classes for extensibility
from .base.queue import BaseTaskQueue
from .base.result_storage import BaseResultStorage
from .base.event_storage import BaseEventStorage
from .base.worker import BaseWorker

# Import serialization manager
from .serialization.manager import SerializationManager

# Import configuration loader
from .config.loader import ConfigLoader

# Expose public API
__all__ = [
    # Main classes
    "OmniQ",
    
    # Models
    "Task",
    "TaskStatus",
    "Schedule",
    "ScheduleType",
    "TaskResult",
    "ResultStatus",
    "TaskEvent",
    "EventType",
    "OmniQConfig",
    
    # Base classes
    "BaseTaskQueue",
    "BaseResultStorage",
    "BaseEventStorage",
    "BaseWorker",
    
    # Utilities
    "SerializationManager",
    "ConfigLoader",
]

# Package-level convenience functions
def create_omniq(
    project_name: str = "omniq",
    config_path: Optional[str] = None,
    **kwargs
) -> OmniQ:
    """Create a new OmniQ instance with default configuration."""
    if config_path:
        return OmniQ.from_config_file(config_path)
    
    config = {"project_name": project_name}
    config.update(kwargs)
    return OmniQ.from_config(config)
```

## Implementation Notes

### Async First, Sync Wrapped Implementation

The implementation follows the "Async First, Sync Wrapped" pattern as specified in the project plan:

1. **Core Implementation**: All core functionality is implemented asynchronously using `async/await` syntax for maximum performance.

2. **Sync Wrappers**: Synchronous methods are provided as thin wrappers around their async counterparts using `anyio.from_thread.run()`.

3. **Consistent Pattern**: Each component follows the same pattern:
   - Async methods with `_async` suffix
   - Sync methods without suffix
   - `_run_async()` helper method for sync wrappers

4. **Context Managers**: Both async and sync context managers are provided for proper resource management.

### Configuration Management

The configuration system supports multiple sources with proper precedence:

1. **Default Values**: Built-in defaults for all settings
2. **Environment Variables**: Override with `OMNIQ_` prefixed variables
3. **YAML Files**: Load from configuration files
4. **Direct Configuration**: Pass configuration objects or dictionaries

### Serialization Strategy

The serialization layer provides intelligent format selection:

1. **Msgspec First**: Try msgspec for high-performance serialization of compatible types
2. **Dill Fallback**: Use dill for complex objects that msgspec can't handle
3. **Format Detection**: Automatically detect the serialization format when deserializing
4. **Security**: Restrict dill deserialization to safe modules

### Extensibility

The base classes provide a clear interface for implementing custom backends:

1. **Abstract Methods**: Define required functionality for each component type
2. **Consistent API**: All implementations follow the same interface
3. **Context Managers**: Proper resource management for all components
4. **Error Handling**: Consistent error handling across implementations

## Testing Strategy

For Task 1, the following tests should be implemented:

1. **Model Tests**: Verify serialization, validation, and business logic of all model classes
2. **Configuration Tests**: Test loading from different sources and precedence rules
3. **Serialization Tests**: Verify serialization/deserialization with different object types
4. **Base Class Tests**: Test abstract method enforcement and basic functionality

## Dependencies

Task 1 requires the following dependencies:

- Core: `msgspec`, `anyio`, `pyyaml`, `python-dateutil`, `croniter`
- Serialization: `dill`
- Development: `pytest`, `pytest-asyncio`, `black`, `isort`, `mypy`, `ruff`

## Deliverables

1. Complete implementation of all core models, base classes, and configuration management
2. Serialization layer with intelligent format selection
3. Core OmniQ class with both async and sync interfaces
4. Package initialization with proper exports
5. Comprehensive test suite for all implemented components
6. Documentation for all public APIs