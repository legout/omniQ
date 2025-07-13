"""Schedule model with timing logic and pause/resume capability."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import msgspec
from croniter import croniter


class ScheduleConfig(msgspec.Struct):
    """Configuration for schedule timing behavior."""
    
    # Cron expression for scheduling
    cron: Optional[str] = None
    
    # Simple interval scheduling
    interval_seconds: Optional[float] = None
    
    # One-time scheduling
    run_at: Optional[float] = None  # Unix timestamp
    
    # Repeat configuration
    max_runs: Optional[int] = None
    run_until: Optional[float] = None  # Unix timestamp
    
    # Timezone handling
    timezone: str = "UTC"
    
    # Jitter and delay
    jitter_seconds: float = 0.0
    initial_delay_seconds: float = 0.0


class Schedule(msgspec.Struct):
    """Schedule model with pause/resume capability and comprehensive timing logic."""
    
    # Core identification
    name: str
    config: ScheduleConfig
    
    # State management
    is_active: bool = True
    is_paused: bool = False
    
    # Execution tracking
    run_count: int = 0
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    
    # Timestamps
    created_at: float = msgspec.field(default_factory=time.time)
    paused_at: Optional[float] = None
    resumed_at: Optional[float] = None
    
    # Metadata
    tags: Dict[str, str] = msgspec.field(default_factory=dict)
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialize schedule after creation."""
        if self.next_run_at is None:
            self.next_run_at = self._calculate_next_run()
    
    def pause(self) -> None:
        """Pause the schedule."""
        if not self.is_paused:
            self.is_paused = True
            self.paused_at = time.time()
    
    def resume(self) -> None:
        """Resume the schedule."""
        if self.is_paused:
            self.is_paused = False
            self.resumed_at = time.time()
            self.paused_at = None
            # Recalculate next run time
            self.next_run_at = self._calculate_next_run()
    
    def deactivate(self) -> None:
        """Permanently deactivate the schedule."""
        self.is_active = False
        self.is_paused = False
    
    def is_due(self) -> bool:
        """Check if schedule is due for execution."""
        if not self.is_active or self.is_paused:
            return False
        
        if self.next_run_at is None:
            return False
        
        return time.time() >= self.next_run_at
    
    def should_continue(self) -> bool:
        """Check if schedule should continue running."""
        if not self.is_active:
            return False
        
        # Check max runs limit
        if self.config.max_runs is not None and self.run_count >= self.config.max_runs:
            return False
        
        # Check run until limit
        if self.config.run_until is not None and time.time() >= self.config.run_until:
            return False
        
        return True
    
    def mark_executed(self) -> None:
        """Mark schedule as executed and calculate next run."""
        self.run_count += 1
        self.last_run_at = time.time()
        
        if self.should_continue():
            self.next_run_at = self._calculate_next_run()
        else:
            self.next_run_at = None
            self.deactivate()
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get next run time as datetime object."""
        if self.next_run_at is None:
            return None
        return datetime.fromtimestamp(self.next_run_at, tz=timezone.utc)
    
    def _calculate_next_run(self) -> Optional[float]:
        """Calculate the next run time based on configuration."""
        now = time.time()
        
        # One-time execution
        if self.config.run_at is not None:
            if self.run_count == 0 and self.config.run_at > now:
                return self.config.run_at
            return None
        
        # Cron-based scheduling
        if self.config.cron is not None:
            try:
                cron = croniter(self.config.cron, now)
                next_time = cron.get_next()
                return next_time + self._get_jitter()
            except (ValueError, TypeError):
                return None
        
        # Interval-based scheduling
        if self.config.interval_seconds is not None:
            if self.run_count == 0:
                # First run with initial delay
                base_time = now + self.config.initial_delay_seconds
            else:
                # Subsequent runs based on interval
                base_time = (self.last_run_at or now) + self.config.interval_seconds
            
            return base_time + self._get_jitter()
        
        return None
    
    def _get_jitter(self) -> float:
        """Get random jitter value."""
        if self.config.jitter_seconds <= 0:
            return 0.0
        
        import random
        return random.uniform(0, self.config.jitter_seconds)
    
    def with_tags(self, **tags: str) -> Schedule:
        """Return new schedule with additional tags."""
        new_tags = {**self.tags, **tags}
        return msgspec.structs.replace(self, tags=new_tags)
    
    def with_metadata(self, **metadata: Any) -> Schedule:
        """Return new schedule with additional metadata."""
        new_metadata = {**self.metadata, **metadata}
        return msgspec.structs.replace(self, metadata=new_metadata)