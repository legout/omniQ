import uuid
from datetime import datetime
from enum import Enum
import msgspec


class TaskEventType(Enum):
    ENQUEUED = "enqueued"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskEvent(msgspec.Struct):
    task_id: uuid.UUID
    event_type: TaskEventType
    timestamp: datetime
    worker_id: str | None = None