import uuid
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
import msgspec


class Task(msgspec.Struct):
    id: uuid.UUID
    func_name: str
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    created_at: datetime
    ttl: timedelta | None = None