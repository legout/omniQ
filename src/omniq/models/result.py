import uuid
from datetime import datetime, timedelta
from typing import Any
from enum import Enum
import msgspec


class TaskStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"


class TaskResult(msgspec.Struct):
    task_id: uuid.UUID
    status: TaskStatus
    result_data: Any
    timestamp: datetime
    ttl: timedelta | None = None