"""
Schedule model for OmniQ.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Union
from enum import Enum

import msgspec
from msgspec import Struct
from croniter import croniter


class ScheduleType(str, Enum):
    """Schedule type enumeration."""
    CRON = "cron"
    INTERVAL = "interval"
    TIMESTAMP = "timestamp"


class ScheduleStatus(str, Enum):
    """Schedule status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Schedule(Struct):
    """
    Represents a scheduled task in OmniQ.
    
    This class handles cron-style scheduling, interval-based scheduling,
    and one-time timestamp scheduling with pause/resume capability.
    """
    
    # Required fields first
    schedule_type: ScheduleType
    func: Union[str, Callable]
    
    # Core identification
    id: str = msgspec.field(default_factory=lambda: str(uuid.uuid4()))
    
    # Schedule configuration
    cron_expression: Optional[str] = None
    interval: Optional[timedelta] = None
    timestamp: Optional[datetime] = None
    
    # Task configuration
    args: tuple = msgspec.field(default_factory=tuple)
    kwargs: Dict[str, Any] = msgspec.field(default_factory=dict)
    queue_name: str = "default"
    
    # Schedule state
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    created_at: datetime = msgspec.field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    # Limits and TTL
    max_runs: Optional[int] = None
    run_count: int = 0
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = msgspec.field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Validate schedule configuration
        self._validate_schedule()
        
        # Set expires_at based on TTL if not already set
        if self.ttl is not None and self.expires_at is None:
            self.expires_at = self.created_at + self.ttl
        
        # Calculate initial next_run if not set
        if self.next_run is None and self.status == ScheduleStatus.ACTIVE:
            self.next_run = self._calculate_next_run()
    
    def _validate_schedule(self) -> None:
        """Validate schedule configuration."""
        if self.schedule_type == ScheduleType.CRON:
            if not self.cron_expression:
                raise ValueError("cron_expression is required for CRON schedule type")
            # Validate cron expression
            try:
                croniter(self.cron_expression)
            except ValueError as e:
                raise ValueError(f"Invalid cron expression: {e}")
        
        elif self.schedule_type == ScheduleType.INTERVAL:
            if not self.interval:
                raise ValueError("interval is required for INTERVAL schedule type")
            if self.interval.total_seconds() <= 0:
                raise ValueError("interval must be positive")
        
        elif self.schedule_type == ScheduleType.TIMESTAMP:
            if not self.timestamp:
                raise ValueError("timestamp is required for TIMESTAMP schedule type")
    
    def _calculate_next_run(self, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate the next run time based on schedule type."""
        if self.status != ScheduleStatus.ACTIVE:
            return None
        
        if self.is_expired():
            return None
        
        if self.max_runs is not None and self.run_count >= self.max_runs:
            return None
        
        base = base_time or datetime.utcnow()
        
        if self.schedule_type == ScheduleType.CRON:
            if self.cron_expression is not None:
                cron = croniter(self.cron_expression, base)
                return cron.get_next(datetime)
        
        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.last_run is None:
                return base
            if self.interval is not None:
                return self.last_run + self.interval
        
        elif self.schedule_type == ScheduleType.TIMESTAMP:
            if self.run_count == 0 and self.timestamp is not None and self.timestamp > base:
                return self.timestamp
            return None  # One-time schedule already executed
        
        return None
    
    def is_expired(self) -> bool:
        """Check if the schedule has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_ready_to_run(self) -> bool:
        """Check if the schedule is ready to create a new task."""
        if self.status != ScheduleStatus.ACTIVE:
            return False
        
        if self.is_expired():
            return False
        
        if self.max_runs is not None and self.run_count >= self.max_runs:
            return False
        
        if self.next_run is None:
            return False
        
        return datetime.utcnow() >= self.next_run
    
    def mark_run(self) -> None:
        """Mark that the schedule has been executed."""
        now = datetime.utcnow()
        self.last_run = now
        self.run_count += 1
        
        # Calculate next run time
        self.next_run = self._calculate_next_run(now)
        
        # Check if schedule should be completed
        if (self.max_runs is not None and self.run_count >= self.max_runs) or \
           (self.schedule_type == ScheduleType.TIMESTAMP and self.run_count > 0):
            self.status = ScheduleStatus.COMPLETED
            self.next_run = None
    
    def pause(self) -> None:
        """Pause the schedule."""
        if self.status == ScheduleStatus.ACTIVE:
            self.status = ScheduleStatus.PAUSED
    
    def resume(self) -> None:
        """Resume the schedule."""
        if self.status == ScheduleStatus.PAUSED:
            self.status = ScheduleStatus.ACTIVE
            self.next_run = self._calculate_next_run()
    
    def cancel(self) -> None:
        """Cancel the schedule."""
        self.status = ScheduleStatus.CANCELLED
        self.next_run = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary representation."""
        return msgspec.to_builtins(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schedule":
        """Create schedule from dictionary representation."""
        return msgspec.convert(data, cls)
    
    @classmethod
    def from_cron(
        cls,
        cron_expression: str,
        func: Union[str, Callable],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        **schedule_kwargs
    ) -> "Schedule":
        """Create a cron-based schedule."""
        return cls(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            func=func,
            args=args,
            kwargs=kwargs or {},
            queue_name=queue_name,
            **schedule_kwargs
        )
    
    @classmethod
    def from_interval(
        cls,
        interval: timedelta,
        func: Union[str, Callable],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        **schedule_kwargs
    ) -> "Schedule":
        """Create an interval-based schedule."""
        return cls(
            schedule_type=ScheduleType.INTERVAL,
            interval=interval,
            func=func,
            args=args,
            kwargs=kwargs or {},
            queue_name=queue_name,
            **schedule_kwargs
        )
    
    @classmethod
    def from_timestamp(
        cls,
        timestamp: datetime,
        func: Union[str, Callable],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: str = "default",
        **schedule_kwargs
    ) -> "Schedule":
        """Create a timestamp-based schedule."""
        return cls(
            schedule_type=ScheduleType.TIMESTAMP,
            timestamp=timestamp,
            func=func,
            args=args,
            kwargs=kwargs or {},
            queue_name=queue_name,
            **schedule_kwargs
        )