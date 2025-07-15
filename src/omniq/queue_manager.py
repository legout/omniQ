"""
Queue Manager for OmniQ.

This module provides advanced queue management capabilities including:
- Queue-specific priority systems
- Cross-queue task routing
- Queue-level configuration management
- Priority algorithm implementations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from collections import defaultdict

from .models.task import Task, TaskStatus
from .models.config import OmniQConfig, QueueConfig
from .storage.base import BaseTaskQueue

logger = logging.getLogger(__name__)


class PriorityAlgorithm:
    """Base class for priority algorithms."""
    
    def calculate_priority(self, task: Task, queue_config: QueueConfig) -> float:
        """Calculate effective priority for a task."""
        raise NotImplementedError


class NumericPriorityAlgorithm(PriorityAlgorithm):
    """Standard numeric priority algorithm (higher number = higher priority)."""
    
    def calculate_priority(self, task: Task, queue_config: QueueConfig) -> float:
        """Return task priority clamped to queue limits."""
        priority = task.priority
        
        # Clamp to queue limits
        if priority > queue_config.max_priority:
            priority = queue_config.max_priority
        elif priority < queue_config.min_priority:
            priority = queue_config.min_priority
            
        return float(priority)


class WeightedPriorityAlgorithm(PriorityAlgorithm):
    """Weighted priority algorithm using queue-specific weights."""
    
    def calculate_priority(self, task: Task, queue_config: QueueConfig) -> float:
        """Calculate weighted priority based on task metadata and queue weights."""
        base_priority = float(task.priority)
        
        # Apply weights from queue configuration
        total_weight = 1.0
        for weight_key, weight_value in queue_config.priority_weights.items():
            if weight_key in task.metadata:
                metadata_value = task.metadata[weight_key]
                if isinstance(metadata_value, (int, float)):
                    total_weight += weight_value * metadata_value
                elif isinstance(metadata_value, bool) and metadata_value:
                    total_weight += weight_value
        
        return base_priority * total_weight


class TimePriorityAlgorithm(PriorityAlgorithm):
    """Time-based priority algorithm (older tasks get higher priority)."""
    
    def calculate_priority(self, task: Task, queue_config: QueueConfig) -> float:
        """Calculate priority based on task age."""
        base_priority = float(task.priority)
        
        # Calculate age in seconds
        age_seconds = (datetime.utcnow() - task.created_at).total_seconds()
        
        # Add age bonus (1 point per hour)
        age_bonus = age_seconds / 3600.0
        
        return base_priority + age_bonus


class QueueManager:
    """
    Advanced queue manager with support for multiple named queues,
    queue-specific priority systems, and cross-queue routing.
    """
    
    def __init__(self, config: OmniQConfig, task_queue: BaseTaskQueue):
        """
        Initialize queue manager.
        
        Args:
            config: OmniQ configuration
            task_queue: Task queue storage backend
        """
        self.config = config
        self.task_queue = task_queue
        
        # Priority algorithms registry
        self._priority_algorithms: Dict[str, PriorityAlgorithm] = {
            "numeric": NumericPriorityAlgorithm(),
            "weighted": WeightedPriorityAlgorithm(),
            "time": TimePriorityAlgorithm(),
        }
        
        # Queue statistics
        self._queue_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "enqueued_count": 0,
            "dequeued_count": 0,
            "current_size": 0,
            "last_activity": None,
        })
        
        # Custom priority functions
        self._custom_priority_functions: Dict[str, Callable] = {}
    
    def register_priority_algorithm(self, name: str, algorithm: PriorityAlgorithm) -> None:
        """Register a custom priority algorithm."""
        self._priority_algorithms[name] = algorithm
        logger.info(f"Registered priority algorithm: {name}")
    
    def register_custom_priority_function(self, name: str, func: Callable[[Task, QueueConfig], float]) -> None:
        """Register a custom priority function."""
        self._custom_priority_functions[name] = func
        logger.info(f"Registered custom priority function: {name}")
    
    def get_effective_priority(self, task: Task) -> float:
        """
        Calculate the effective priority for a task based on its queue configuration.
        
        Args:
            task: The task to calculate priority for
            
        Returns:
            Effective priority value
        """
        queue_config = self.config.get_queue_config(task.queue_name)
        
        # Get priority algorithm
        algorithm_name = queue_config.priority_algorithm
        
        if algorithm_name == "custom" and queue_config.custom_priority_func:
            # Use custom function
            if queue_config.custom_priority_func in self._custom_priority_functions:
                func = self._custom_priority_functions[queue_config.custom_priority_func]
                return func(task, queue_config)
            else:
                logger.warning(f"Custom priority function '{queue_config.custom_priority_func}' not found, using numeric")
                algorithm_name = "numeric"
        
        # Use registered algorithm
        if algorithm_name in self._priority_algorithms:
            algorithm = self._priority_algorithms[algorithm_name]
            return algorithm.calculate_priority(task, queue_config)
        else:
            logger.warning(f"Priority algorithm '{algorithm_name}' not found, using numeric")
            algorithm = self._priority_algorithms["numeric"]
            return algorithm.calculate_priority(task, queue_config)
    
    async def enqueue_with_validation(self, task: Task) -> str:
        """
        Enqueue a task with queue-specific validation and priority calculation.
        
        Args:
            task: The task to enqueue
            
        Returns:
            Task ID
            
        Raises:
            ValueError: If queue validation fails
        """
        queue_config = self.config.get_queue_config(task.queue_name)
        
        # Validate queue capacity
        if queue_config.max_size is not None:
            current_size = await self.task_queue.get_queue_size(task.queue_name)
            if current_size >= queue_config.max_size:
                raise ValueError(f"Queue '{task.queue_name}' is at capacity ({queue_config.max_size})")
        
        # Apply queue-specific defaults
        if task.priority == 0:  # Use queue default if not specified
            task.priority = queue_config.default_priority
        
        # Calculate and apply effective priority using the configured algorithm
        effective_priority = self.get_effective_priority(task)
        # Clamp to queue limits
        if effective_priority > queue_config.max_priority:
            effective_priority = queue_config.max_priority
        elif effective_priority < queue_config.min_priority:
            effective_priority = queue_config.min_priority
        task.priority = int(effective_priority)
        
        # Apply queue-specific timeout
        if queue_config.timeout and not task.expires_at:
            task.expires_at = datetime.utcnow() + timedelta(seconds=queue_config.timeout)
        
        # Apply queue-specific retry settings
        if queue_config.max_retries is not None:
            task.max_retries = queue_config.max_retries
        if queue_config.retry_delay is not None:
            task.retry_delay = timedelta(seconds=queue_config.retry_delay)
        
        # Enqueue the task
        task_id = await self.task_queue.enqueue(task)
        
        # Update statistics
        self._queue_stats[task.queue_name]["enqueued_count"] += 1
        self._queue_stats[task.queue_name]["current_size"] += 1
        self._queue_stats[task.queue_name]["last_activity"] = datetime.utcnow()
        
        logger.debug(f"Enqueued task {task_id} to queue '{task.queue_name}' with priority {task.priority}")
        return task_id
    
    async def dequeue_with_routing(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """
        Dequeue a task using advanced routing strategies.
        
        Args:
            queues: List of queue names to check
            timeout: Maximum time to wait for a task
            
        Returns:
            Next available task or None
        """
        if not queues:
            return None
        
        # Apply queue routing strategy
        if self.config.queue_routing_strategy == "priority":
            ordered_queues = self._order_queues_by_priority(queues)
        elif self.config.queue_routing_strategy == "weighted":
            ordered_queues = self._order_queues_by_weight(queues)
        else:  # round_robin
            ordered_queues = queues
        
        # Try to dequeue from ordered queues
        task = await self.task_queue.dequeue(ordered_queues, timeout)
        
        if task:
            # Update statistics
            self._queue_stats[task.queue_name]["dequeued_count"] += 1
            self._queue_stats[task.queue_name]["current_size"] -= 1
            self._queue_stats[task.queue_name]["last_activity"] = datetime.utcnow()
            
            logger.debug(f"Dequeued task {task.id} from queue '{task.queue_name}'")
        
        return task
    
    def _order_queues_by_priority(self, queues: List[str]) -> List[str]:
        """Order queues by their configured priority."""
        def get_queue_priority(queue_name: str) -> int:
            queue_config = self.config.get_queue_config(queue_name)
            return queue_config.default_priority
        
        return sorted(queues, key=get_queue_priority, reverse=True)
    
    def _order_queues_by_weight(self, queues: List[str]) -> List[str]:
        """Order queues by weighted selection (simplified version)."""
        # For now, use priority-based ordering
        # In a full implementation, this would use weighted random selection
        return self._order_queues_by_priority(queues)
    
    async def move_task_between_queues(self, task_id: str, target_queue: str) -> bool:
        """
        Move a task from one queue to another.
        
        Args:
            task_id: ID of the task to move
            target_queue: Name of the target queue
            
        Returns:
            True if task was moved successfully
        """
        # Get the task
        task = await self.task_queue.get_task(task_id)
        if not task:
            return False
        
        # Validate target queue
        target_config = self.config.get_queue_config(target_queue)
        if target_config.max_size is not None:
            current_size = await self.task_queue.get_queue_size(target_queue)
            if current_size >= target_config.max_size:
                raise ValueError(f"Target queue '{target_queue}' is at capacity")
        
        # Update task queue
        old_queue = task.queue_name
        task.queue_name = target_queue
        
        # Apply target queue defaults
        task.priority = target_config.default_priority
        
        # Update the task
        await self.task_queue.update_task(task)
        
        # Update statistics
        self._queue_stats[old_queue]["current_size"] -= 1
        self._queue_stats[target_queue]["current_size"] += 1
        
        logger.info(f"Moved task {task_id} from queue '{old_queue}' to '{target_queue}'")
        return True
    
    async def get_queue_statistics(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Args:
            queue_name: Specific queue name, or None for all queues
            
        Returns:
            Dictionary of queue statistics
        """
        if queue_name:
            stats = dict(self._queue_stats[queue_name])
            # Get real-time size
            stats["current_size"] = await self.task_queue.get_queue_size(queue_name)
            return {queue_name: stats}
        else:
            all_stats = {}
            for qname in self._queue_stats:
                stats = dict(self._queue_stats[qname])
                stats["current_size"] = await self.task_queue.get_queue_size(qname)
                all_stats[qname] = stats
            return all_stats
    
    def get_queue_config(self, queue_name: str) -> QueueConfig:
        """Get configuration for a specific queue."""
        return self.config.get_queue_config(queue_name)
    
    def update_queue_config(self, queue_config: QueueConfig) -> None:
        """Update configuration for a queue."""
        self.config.add_queue_config(queue_config)
        logger.info(f"Updated configuration for queue '{queue_config.name}'")
    
    def list_queues(self) -> List[str]:
        """List all configured queue names."""
        return self.config.list_queue_names()
    
    async def cleanup_empty_queues(self) -> List[str]:
        """
        Clean up queues that have no tasks and haven't been active recently.
        
        Returns:
            List of cleaned up queue names
        """
        cleaned_queues = []
        current_time = datetime.utcnow()
        
        for queue_name in list(self._queue_stats.keys()):
            stats = self._queue_stats[queue_name]
            queue_size = await self.task_queue.get_queue_size(queue_name)
            
            # Check if queue is empty and inactive
            if queue_size == 0 and stats["last_activity"]:
                time_since_activity = (current_time - stats["last_activity"]).total_seconds()
                if time_since_activity > 3600:  # 1 hour of inactivity
                    del self._queue_stats[queue_name]
                    cleaned_queues.append(queue_name)
        
        if cleaned_queues:
            logger.info(f"Cleaned up empty queues: {cleaned_queues}")
        
        return cleaned_queues