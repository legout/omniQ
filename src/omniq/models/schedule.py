from typing import Any, Dict, Optional, Union
from msgspec import Struct, field
from datetime import datetime
import uuid
import pytz

class Schedule(Struct):
    """
    Represents a schedule for task execution with timing logic and pause/resume capability.
    Supports cron-based, interval-based, and one-time scheduling.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_data: Dict[str, Any] = field(default_factory=dict)  # Data to create a Task when triggered
    timing_type: str = field(default="interval")  # "cron", "interval", or "timestamp"
    timing_value: Union[str, float, int] = field()  # type: ignore #
    is_active: bool = True  # Schedule state: active or paused
    last_execution: Optional[float] = None  # Timestamp of last execution
    next_execution: Optional[float] = None  # Timestamp of next planned execution
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    timezone: str = field(default="UTC")  # Timezone for schedule execution, e.g., "US/Pacific"
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def pause(self) -> None:
        """Pause the schedule to prevent further executions."""
        self.is_active = False

    def resume(self) -> None:
        """Resume the schedule to allow executions."""
        self.is_active = True

    def is_due(self) -> bool:
        """Check if the schedule is due for execution based on timing logic."""
        if not self.is_active:
            return False
        
        # Get current time in the specified timezone
        tz = pytz.timezone(self.timezone)
        current_time = datetime.now(tz).timestamp()
        
        if self.timing_type == "timestamp":
            if isinstance(self.timing_value, (int, float)):
                return current_time >= self.timing_value
            return False
        
        elif self.timing_type == "interval":
            if self.last_execution is None:
                return True
            if isinstance(self.timing_value, (int, float)):
                return current_time >= self.last_execution + self.timing_value
            return False
            
        elif self.timing_type == "cron":
            # TODO: Implement cron parsing logic using a library like 'croniter'
            # This will parse the cron expression in timing_value and check if current time matches
            return False
            
        return False
