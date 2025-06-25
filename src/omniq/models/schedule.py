# src/omniq/models/schedule.py
"""Schedule model for OmniQ."""

import uuid
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import msgspec

class Schedule(msgspec.Struct):
    """Schedule model for OmniQ."""
    
    id: str
    func: Union[Callable, str]  # Function or function name
    func_args: Dict[str, Any]
    queue_name: str
    created_at: datetime
    next_run_at: datetime
    last_run_at: Optional[datetime] = None
    interval: Optional[timedelta] = None
    cron: Optional[str] = None
    ttl: Optional[timedelta] = None
    result_ttl: Optional[timedelta] = None
    active: bool = True
    
    @classmethod
    def create(
        cls,
        func: Union[Callable, str],
        func_args: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        interval: Optional[timedelta] = None,
        cron: Optional[str] = None,
        ttl: Optional[timedelta] = None,
        result_ttl: Optional[timedelta] = None
    ) -> "Schedule":
        """Create a new schedule."""
        if interval is None and cron is None:
            raise ValueError("Either interval or cron must be specified")

        now = datetime.now()

        # For simplicity, we'll just use interval for now
        next_run_at = now
        if interval is not None:
            next_run_at = now + interval
        
        return cls(
            id=str(uuid.uuid4()),
            func=func,
            func_args=func_args or {},
            queue_name=queue_name,
            interval=interval,
            cron=cron,
            created_at=now,
            next_run_at=next_run_at,
            ttl=ttl,
            result_ttl=result_ttl
        )
    
    def calculate_next_run(self) -> datetime:
        """Calculate the next run time."""
        now = datetime.utcnow()
        
        if self.interval is not None:
            if self.last_run_at is not None:
                return self.last_run_at + self.interval
            return now + self.interval
        
        # For simplicity, we'll just add a default interval for cron
        # In a real implementation, this would parse the cron expression
        return now + timedelta(minutes=5)
    
    def update_after_run(self) -> None:
        """Update schedule after a run."""
        self.last_run_at = datetime.utcnow()
        self.next_run_at = self.calculate_next_run()
    
    def pause(self) -> None:
        """Pause the schedule."""
        self.active = False
    
    def resume(self) -> None:
        """Resume the schedule."""
        self.active = True
        self.next_run_at = self.calculate_next_run()