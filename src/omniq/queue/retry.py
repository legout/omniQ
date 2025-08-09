import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List
import logging

from ..models.task import Task
from ..models.result import TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class RetryManager:
    """
    Manages task retries with exponential backoff and jitter.
    
    This class handles retrying failed tasks with configurable retry policies,
    including exponential backoff with jitter to prevent thundering herd problems.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[type]] = None
    ):
        """
        Initialize the RetryManager.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delay
            retryable_exceptions: List of exception types that should be retried
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self._retry_counts: Dict[uuid.UUID, int] = {}
        self._retry_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        
    async def should_retry(self, task: Task, exception: Exception) -> bool:
        """
        Determine if a task should be retried based on the exception and retry count.
        
        Args:
            task: The task that failed
            exception: The exception that caused the failure
            
        Returns:
            True if the task should be retried, False otherwise
        """
        # Check if the exception is retryable
        if not any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions):
            return False
            
        # Check if we've exceeded max retries
        retry_count = self._retry_counts.get(task.id, 0)
        return retry_count < self.max_retries
    
    async def schedule_retry(self, task: Task, exception: Exception, retry_callback: Callable) -> None:
        """
        Schedule a task for retry with appropriate delay.
        
        Args:
            task: The task to retry
            exception: The exception that caused the failure
            retry_callback: Callback function to execute the retry
        """
        retry_count = self._retry_counts.get(task.id, 0) + 1
        self._retry_counts[task.id] = retry_count
        
        # Calculate delay with exponential backoff and jitter
        delay = self._calculate_delay(retry_count)
        
        logger.info(
            f"Scheduling retry {retry_count}/{self.max_retries} for task {task.id} "
            f"after {delay:.2f}s delay. Exception: {type(exception).__name__}: {str(exception)}"
        )
        
        # Create and store the retry task
        retry_task = asyncio.create_task(self._execute_retry_after_delay(task, delay, retry_callback))
        self._retry_tasks[task.id] = retry_task
        
    async def _execute_retry_after_delay(self, task: Task, delay: float, retry_callback: Callable) -> None:
        """
        Execute the retry callback after the specified delay.
        
        Args:
            task: The task to retry
            delay: Delay in seconds before retrying
            retry_callback: Callback function to execute the retry
        """
        try:
            await asyncio.sleep(delay)
            await retry_callback(task)
        except Exception as e:
            logger.error(f"Error during retry execution for task {task.id}: {e}")
        finally:
            # Clean up the retry task reference
            self._retry_tasks.pop(task.id, None)
    
    def _calculate_delay(self, retry_count: int) -> float:
        """
        Calculate the delay for a retry attempt using exponential backoff with jitter.
        
        Args:
            retry_count: The current retry attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = self.base_delay * (self.exponential_base ** (retry_count - 1))
        
        # Cap at maximum delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # 50% to 100% of calculated delay
            
        return delay
    
    async def cancel_retry(self, task_id: uuid.UUID) -> bool:
        """
        Cancel a pending retry for a task.
        
        Args:
            task_id: ID of the task to cancel retry for
            
        Returns:
            True if a retry was cancelled, False if no retry was pending
        """
        retry_task = self._retry_tasks.pop(task_id, None)
        if retry_task:
            retry_task.cancel()
            self._retry_counts.pop(task_id, None)
            return True
        return False
    
    def get_retry_count(self, task_id: uuid.UUID) -> int:
        """
        Get the current retry count for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Current retry count
        """
        return self._retry_counts.get(task_id, 0)
    
    def is_retry_pending(self, task_id: uuid.UUID) -> bool:
        """
        Check if a retry is pending for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            True if a retry is pending, False otherwise
        """
        return task_id in self._retry_tasks
    
    async def cleanup_task(self, task_id: uuid.UUID) -> None:
        """
        Clean up retry state for a task.
        
        Args:
            task_id: ID of the task to clean up
        """
        await self.cancel_retry(task_id)
        self._retry_counts.pop(task_id, None)
    
    async def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current retry state.
        
        Returns:
            Dictionary containing retry statistics
        """
        return {
            "pending_retries": len(self._retry_tasks),
            "tracked_tasks": len(self._retry_counts),
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "exponential_base": self.exponential_base,
            "jitter_enabled": self.jitter
        }
    
    async def __aenter__(self) -> "RetryManager":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Cancel all pending retries
        for task_id, retry_task in list(self._retry_tasks.items()):
            retry_task.cancel()
            logger.info(f"Cancelled pending retry for task {task_id}")
        
        self._retry_tasks.clear()
        self._retry_counts.clear()