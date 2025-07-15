"""
Configuration models for OmniQ.
"""

import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import msgspec
from msgspec import Struct


class Settings:
    """
    Library settings constants without "OMNIQ_" prefix.
    These can be overridden by environment variables with "OMNIQ_" prefix.
    """
    
    # Logging
    LOG_LEVEL = "INFO"
    DISABLE_LOGGING = False
    
    # Storage backends
    TASK_QUEUE_TYPE = "sqlite"
    TASK_QUEUE_URL = None
    RESULT_STORAGE_TYPE = None  # Defaults to same as task queue
    RESULT_STORAGE_URL = None
    EVENT_STORAGE_TYPE = None  # Defaults to same as task queue
    EVENT_STORAGE_URL = None
    SCHEDULE_STORAGE_TYPE = None  # Defaults to same as task queue
    SCHEDULE_STORAGE_URL = None
    
    # File storage
    BASE_DIR = "./omniq_data"
    FSSPEC_URI = None
    
    # Workers
    DEFAULT_WORKER = "async"
    MAX_WORKERS = 10
    THREAD_WORKERS = 10
    PROCESS_WORKERS = 4
    GEVENT_WORKERS = 100
    
    # Task settings
    TASK_TIMEOUT = 300  # 5 minutes
    TASK_TTL = 3600  # 1 hour
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds
    RESULT_TTL = 86400  # 24 hours
    
    # Component log levels (JSON string)
    COMPONENT_LOG_LEVELS = "{}"


def get_env_setting(key: str, default: Any = None) -> Any:
    """Get setting from environment variable with OMNIQ_ prefix."""
    env_key = f"OMNIQ_{key}"
    env_value = os.environ.get(env_key)
    
    if env_value is None:
        return getattr(Settings, key, default)
    
    # Convert string values to appropriate types
    setting_value = getattr(Settings, key, default)
    if isinstance(setting_value, bool):
        return env_value.lower() in ("1", "true", "yes", "on")
    elif isinstance(setting_value, int):
        return int(env_value)
    elif isinstance(setting_value, float):
        return float(env_value)
    
    return env_value


class BaseConfig(Struct):
    """Base configuration class with advanced loading capabilities."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return msgspec.to_builtins(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create config from dictionary."""
        return msgspec.convert(data, cls)
    
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]):
        """Create config from YAML file."""
        from ..config import load_config_from_yaml
        return load_config_from_yaml(config_path, cls)
    
    @classmethod
    def from_env(cls, prefix: str = "OMNIQ"):
        """Create config from environment variables."""
        env_dict = {}
        prefix_with_underscore = f"{prefix}_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix_with_underscore):
                config_key = key[len(prefix_with_underscore):].lower()
                env_dict[config_key] = value
        
        return cls.from_dict(env_dict)
    
    def merge(self, other: Union["BaseConfig", Dict[str, Any]]) -> "BaseConfig":
        """Merge this config with another config or dictionary."""
        from ..config import config_manager
        
        if isinstance(other, BaseConfig):
            other_dict = other.to_dict()
        else:
            other_dict = other
            
        merged_dict = config_manager.loader.merge_configs(self.to_dict(), other_dict)
        return self.__class__.from_dict(merged_dict)
    
    def update(self, **kwargs) -> "BaseConfig":
        """Update config with new values."""
        return self.merge(kwargs)


class SQLiteConfig(BaseConfig):
    """SQLite backend configuration."""
    
    # Database file path
    database_path: str = "omniq.db"
    
    # Connection settings
    timeout: float = 30.0
    check_same_thread: bool = False
    
    # Performance settings
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = -64000  # 64MB
    
    # Table settings
    tasks_table: str = "tasks"
    results_table: str = "results"
    events_table: str = "events"
    schedules_table: str = "schedules"
    
    # Cleanup settings
    cleanup_interval: int = 3600  # 1 hour
    auto_vacuum: bool = True


class FileConfig(BaseConfig):
    """File backend configuration."""
    
    # Base directory for file storage
    base_dir: str = "./omniq_data"
    
    # fsspec URI (e.g., "s3://bucket", "memory://")
    fsspec_uri: Optional[str] = None
    
    # Storage options for fsspec
    storage_options: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # File organization
    tasks_dir: str = "tasks"
    results_dir: str = "results"
    events_dir: str = "events"
    schedules_dir: str = "schedules"
    
    # Serialization format
    serialization_format: str = "json"  # json, msgpack, pickle


class PostgresConfig(BaseConfig):
    """PostgreSQL backend configuration."""
    
    # Connection settings
    host: str = "localhost"
    port: int = 5432
    database: str = "omniq"
    username: str = "postgres"
    password: str = ""
    
    # Connection pool settings
    min_connections: int = 1
    max_connections: int = 10
    
    # SSL settings
    ssl: bool = False
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    # Table settings
    schema: str = "public"
    tasks_table: str = "tasks"
    results_table: str = "results"
    events_table: str = "events"
    schedules_table: str = "schedules"
    
    # Performance settings
    command_timeout: float = 60.0
    query_timeout: float = 30.0


class RedisConfig(BaseConfig):
    """Redis backend configuration."""
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    
    # Connection pool settings
    max_connections: int = 10
    retry_on_timeout: bool = True
    
    # SSL settings
    ssl: bool = False
    ssl_cert_reqs: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    
    # Key prefixes
    tasks_prefix: str = "omniq:tasks"
    results_prefix: str = "omniq:results"
    events_prefix: str = "omniq:events"
    schedules_prefix: str = "omniq:schedules"
    
    # Performance settings
    socket_timeout: float = 30.0
    socket_connect_timeout: float = 30.0


class NATSConfig(BaseConfig):
    """NATS backend configuration."""
    
    # Connection settings
    servers: List[str] = msgspec.field(default_factory=lambda: ["nats://localhost:4222"])
    
    # Authentication
    user: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    
    # TLS settings
    tls: bool = False
    tls_cert: Optional[str] = None
    tls_key: Optional[str] = None
    tls_ca: Optional[str] = None
    
    # Subject prefixes
    tasks_subject: str = "omniq.tasks"
    results_subject: str = "omniq.results"
    events_subject: str = "omniq.events"
    schedules_subject: str = "omniq.schedules"
    
    # Performance settings
    connect_timeout: float = 2.0
    reconnect_time_wait: float = 2.0
    max_reconnect_attempts: int = 60
    
    # Queue groups
    queue_group: str = "omniq_workers"


class QueueConfig(BaseConfig):
    """Configuration for individual queue settings."""
    
    # Queue identification
    name: str
    
    # Priority settings
    priority_algorithm: str = "numeric"  # numeric, weighted, custom
    default_priority: int = 0
    max_priority: int = 100
    min_priority: int = -100
    
    # Capacity settings
    max_size: Optional[int] = None  # None = unlimited
    max_concurrency: Optional[int] = None  # None = unlimited
    
    # Processing settings
    batch_size: int = 1
    timeout: Optional[float] = None  # Queue-specific timeout
    
    # Retry settings
    max_retries: Optional[int] = None  # Override global setting
    retry_delay: Optional[float] = None  # Override global setting
    
    # Queue-specific metadata
    description: Optional[str] = None
    tags: List[str] = msgspec.field(default_factory=list)
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    # Advanced features
    priority_weights: Dict[str, float] = msgspec.field(default_factory=dict)  # For weighted priority
    custom_priority_func: Optional[str] = None  # For custom priority algorithms


class WorkerConfig(BaseConfig):
    """Worker configuration."""
    
    # Worker type
    worker_type: str = "async"  # async, thread, process, gevent
    
    # Pool settings
    max_workers: int = 10
    
    # Queue processing
    queues: List[str] = msgspec.field(default_factory=lambda: ["default"])
    queue_priorities: Dict[str, int] = msgspec.field(default_factory=dict)  # Queue processing priorities
    poll_interval: float = 1.0
    batch_size: int = 1
    
    # Task execution
    task_timeout: float = 300.0  # 5 minutes
    graceful_shutdown_timeout: float = 30.0
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Monitoring
    heartbeat_interval: float = 30.0
    metrics_enabled: bool = True


class StorageBackendConfig(BaseConfig):
    """Configuration for individual storage backend selection."""
    
    # Backend type (sqlite, file, redis, postgres, nats, memory, etc.)
    backend_type: str = "sqlite"
    
    # Backend-specific configuration
    config: Optional[Dict[str, Any]] = None
    
    # Connection URL (alternative to config dict)
    url: Optional[str] = None


class OmniQConfig(BaseConfig):
    """Main OmniQ configuration."""
    
    # Project settings
    project_name: str = "omniq"
    
    # Independent storage backend configurations
    task_queue_backend: Optional[StorageBackendConfig] = None
    result_storage_backend: Optional[StorageBackendConfig] = None
    event_storage_backend: Optional[StorageBackendConfig] = None
    schedule_storage_backend: Optional[StorageBackendConfig] = None
    
    # Queue configurations
    queues: Dict[str, QueueConfig] = msgspec.field(default_factory=dict)
    
    # Legacy component configurations (for backward compatibility)
    task_queue: Optional[Dict[str, Any]] = None
    result_storage: Optional[Dict[str, Any]] = None
    event_storage: Optional[Dict[str, Any]] = None
    worker: Optional[Dict[str, Any]] = None
    
    # Default settings
    default_queue: str = "default"
    default_ttl: Optional[int] = None  # seconds
    default_result_ttl: Optional[int] = None  # seconds
    
    # Global queue settings
    global_max_priority: int = 100
    global_min_priority: int = -100
    global_default_priority: int = 0
    
    # Cross-queue routing settings
    enable_cross_queue_routing: bool = True
    queue_routing_strategy: str = "priority"  # priority, round_robin, weighted
    
    # Logging
    log_level: str = "INFO"
    disable_logging: bool = False
    component_log_levels: Dict[str, str] = msgspec.field(default_factory=dict)
    
    def get_queue_config(self, queue_name: str) -> QueueConfig:
        """Get configuration for a specific queue, creating default if not exists."""
        if queue_name not in self.queues:
            self.queues[queue_name] = QueueConfig(
                name=queue_name,
                default_priority=self.global_default_priority,
                max_priority=self.global_max_priority,
                min_priority=self.global_min_priority
            )
        return self.queues[queue_name]
    
    def add_queue_config(self, queue_config: QueueConfig) -> None:
        """Add or update a queue configuration."""
        self.queues[queue_config.name] = queue_config
    
    def remove_queue_config(self, queue_name: str) -> bool:
        """Remove a queue configuration."""
        if queue_name in self.queues:
            del self.queues[queue_name]
            return True
        return False
    
    def list_queue_names(self) -> List[str]:
        """Get list of configured queue names."""
        return list(self.queues.keys())
    
    def get_task_queue_backend_config(self) -> StorageBackendConfig:
        """Get task queue backend configuration with fallbacks."""
        if self.task_queue_backend:
            return self.task_queue_backend
        
        # Fallback to environment variables
        backend_type = get_env_setting("TASK_QUEUE_TYPE", "sqlite")
        url = get_env_setting("TASK_QUEUE_URL")
        
        return StorageBackendConfig(
            backend_type=backend_type,
            url=url,
            config=self.task_queue
        )
    
    def get_result_storage_backend_config(self) -> StorageBackendConfig:
        """Get result storage backend configuration with fallbacks."""
        if self.result_storage_backend:
            return self.result_storage_backend
        
        # Fallback to environment variables or task queue backend
        backend_type = get_env_setting("RESULT_STORAGE_TYPE") or get_env_setting("TASK_QUEUE_TYPE", "sqlite")
        url = get_env_setting("RESULT_STORAGE_URL") or get_env_setting("TASK_QUEUE_URL")
        
        return StorageBackendConfig(
            backend_type=backend_type,
            url=url,
            config=self.result_storage
        )
    
    def get_event_storage_backend_config(self) -> StorageBackendConfig:
        """Get event storage backend configuration with fallbacks."""
        if self.event_storage_backend:
            return self.event_storage_backend
        
        # Fallback to environment variables or task queue backend
        backend_type = get_env_setting("EVENT_STORAGE_TYPE") or get_env_setting("TASK_QUEUE_TYPE", "sqlite")
        url = get_env_setting("EVENT_STORAGE_URL") or get_env_setting("TASK_QUEUE_URL")
        
        return StorageBackendConfig(
            backend_type=backend_type,
            url=url,
            config=self.event_storage
        )
    
    def get_schedule_storage_backend_config(self) -> StorageBackendConfig:
        """Get schedule storage backend configuration with fallbacks."""
        if self.schedule_storage_backend:
            return self.schedule_storage_backend
        
        # Fallback to environment variables or task queue backend
        backend_type = get_env_setting("SCHEDULE_STORAGE_TYPE") or get_env_setting("TASK_QUEUE_TYPE", "sqlite")
        url = get_env_setting("SCHEDULE_STORAGE_URL") or get_env_setting("TASK_QUEUE_URL")
        
        return StorageBackendConfig(
            backend_type=backend_type,
            url=url
        )
    
    @classmethod
    def from_env(cls, prefix: str = "OMNIQ") -> "OmniQConfig":
        """Create configuration from environment variables."""
        return cls(
            project_name=get_env_setting("PROJECT_NAME", "omniq"),
            default_queue=get_env_setting("DEFAULT_QUEUE", "default"),
            default_ttl=get_env_setting("TASK_TTL"),
            default_result_ttl=get_env_setting("RESULT_TTL"),
            log_level=get_env_setting("LOG_LEVEL", "INFO"),
            disable_logging=get_env_setting("DISABLE_LOGGING", False),
        )