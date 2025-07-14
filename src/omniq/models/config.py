from __future__ import annotations
from typing import Literal
import msgspec

class BaseConfig(msgspec.Struct, kw_only=True):
    project_name: str = "omniq"

class FileStorageConfig(BaseConfig):
    base_dir: str

class SQLiteStorageConfig(BaseConfig):
    base_dir: str

class PostgresStorageConfig(BaseConfig):
    host: str
    port: int = 5432
    user: str
    password: str
    database: str

class RedisStorageConfig(BaseConfig):
    host: str
    port: int = 6379
    db: int = 0

class NatsStorageConfig(BaseConfig):
    servers: list[str]

class TaskQueueConfig(msgspec.Struct, kw_only=True):
    type: Literal["file", "sqlite", "postgres", "redis", "nats"]
    config: FileStorageConfig | SQLiteStorageConfig | PostgresStorageConfig | RedisStorageConfig | NatsStorageConfig

class ResultStorageConfig(msgspec.Struct, kw_only=True):
    type: Literal["file", "sqlite", "postgres", "redis", "nats"]
    config: FileStorageConfig | SQLiteStorageConfig | PostgresStorageConfig | RedisStorageConfig | NatsStorageConfig

class EventStorageConfig(msgspec.Struct, kw_only=True):
    type: Literal["file", "sqlite", "postgres"]
    config: FileStorageConfig | SQLiteStorageConfig | PostgresStorageConfig

class WorkerConfig(msgspec.Struct, kw_only=True):
    type: Literal["async", "thread", "process", "gevent"]
    max_workers: int = 10

class OmniQConfig(BaseConfig):
    task_queue: TaskQueueConfig
    result_storage: ResultStorageConfig
    event_storage: EventStorageConfig | None = None
    worker: WorkerConfig
