from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine
import msgspec
from croniter import croniter

class Schedule(msgspec.Struct, kw_only=True):
    """
    Defines the schedule for a recurring task.
    """
    # Core task information
    func: Callable[..., Any] | Coroutine[Any, Any, Any]
    func_args: dict[str, Any] = {}

    # Schedule information
    id: str
    cron: str | None = None
    interval: timedelta | None = None
    
    # State management
    is_active: bool = True
    
    # Last run tracking
    last_run_at: datetime | None = None

    def __post_init__(self):
        if self.cron is None and self.interval is None:
            raise ValueError("Either 'cron' or 'interval' must be provided.")
        if self.cron and not croniter.is_valid(self.cron):
            raise ValueError(f"Invalid cron string: {self.cron}")

    def get_next_run_time(self, now: datetime | None = None) -> datetime | None:
        """Calculates the next run time based on the schedule."""
        if not self.is_active:
            return None
        
        now = now or datetime.now()
        
        if self.cron:
            return croniter(self.cron, now).get_next(datetime)
        
        if self.interval:
            if self.last_run_at:
                return self.last_run_at + self.interval
            else:
                return now + self.interval
        
        return None
