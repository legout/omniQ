"""Schedule model for OmniQ.

This module defines the Schedule struct for managing recurring tasks:
- Schedule: Model for scheduled tasks with interval or cron expressions

All models use msgspec.Struct for efficient serialization.
"""

import uuid
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional
import msgspec


class Schedule(msgspec.Struct, kw_only=True):
    """Schedule model for recurring tasks.
    
    This model represents a scheduled task that can run based on:
    - Fixed intervals (using timedelta)
    - Cron expressions (for complex scheduling)
    - Specific time windows (start_at, end_at)
    
    The schedule supports pause/resume functionality and tracks
    execution history with last_run_at and next_run_at.
    """
    id: uuid.UUID
    func_name: str
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    start_at: datetime
    interval: Optional[timedelta] = None
    cron: Optional[str] = None
    end_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    is_paused: bool = False
    queue_name: str = "default"
    
    def pause(self) -> None:
        """Pause the schedule.
        
        This prevents the schedule from generating new tasks
        until it is resumed.
        """
        self.is_paused = True
    
    def resume(self) -> None:
        """Resume the schedule.
        
        This allows the schedule to continue generating tasks.
        If next_run_at is not set, it will be calculated.
        """
        self.is_paused = False
    
    def is_active(self, current_time: datetime) -> bool:
        """Check if the schedule is currently active.
        
        A schedule is active if:
        - It is not paused
        - The current time is after start_at
        - The current time is before end_at (if end_at is set)
        
        Args:
            current_time: The current datetime to check against
            
        Returns:
            True if the schedule is active, False otherwise
        """
        if self.is_paused:
            return False
            
        if current_time < self.start_at:
            return False
            
        if self.end_at is not None and current_time > self.end_at:
            return False
            
        return True
    
    def should_run(self, current_time: datetime) -> bool:
        """Check if the schedule should run now.
        
        A schedule should run if:
        - It is active
        - The next_run_at is set and current_time is past it
        - Either interval or cron is set (but not both)
        
        Args:
            current_time: The current datetime to check against
            
        Returns:
            True if the schedule should run, False otherwise
        """
        if not self.is_active(current_time):
            return False
            
        if self.next_run_at is None:
            return False
            
        if current_time < self.next_run_at:
            return False
            
        # Must have either interval or cron, but not both
        if self.interval is None and self.cron is None:
            return False
            
        if self.interval is not None and self.cron is not None:
            return False
            
        return True
    
    def calculate_next_run(self, current_time: datetime) -> Optional[datetime]:
        """Calculate the next run time for the schedule.
        
        Args:
            current_time: The current datetime to calculate from
            
        Returns:
            The next run datetime, or None if it cannot be calculated
        """
        if not self.is_active(current_time):
            return None
            
        if self.interval is not None:
            # For interval-based schedules, add interval to last_run_at or start_at
            base_time = self.last_run_at or self.start_at
            return base_time + self.interval
            
        elif self.cron is not None:
            # For cron-based schedules, we would need a cron parser
            # For now, return None - this would be implemented with a cron library
            return None
            
        return None
    
    def update_after_run(self, run_time: datetime) -> None:
        """Update the schedule after a run.
        
        This updates last_run_at and calculates the next_run_at.
        
        Args:
            run_time: The datetime when the task was run
        """
        self.last_run_at = run_time
        self.next_run_at = self.calculate_next_run(run_time)