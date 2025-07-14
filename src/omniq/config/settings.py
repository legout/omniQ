from __future__ import annotations

# Logging
LOG_LEVEL: str = "INFO"

# Task Queue
TASK_QUEUE_TYPE: str = "memory"

# Result Storage
RESULT_STORAGE_TYPE: str = "memory"

# Event Storage
EVENT_STORAGE_TYPE: str | None = None

# Worker
DEFAULT_WORKER: str = "thread"
MAX_WORKERS: int = 10

# Task
TASK_TTL: int = 3600  # 1 hour
RESULT_TTL: int = 3600  # 1 hour
