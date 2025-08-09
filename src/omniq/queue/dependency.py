"""Dependency management for OmniQ.

This module provides the dependency resolver for managing task dependencies:
- DependencyResolver: Manages task dependency graphs and determines when tasks are ready

The dependency resolver ensures that tasks are only enqueued when their
dependencies are satisfied.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
import logging

from ..models.task import Task
from ..models.result import TaskResult, TaskStatus
from ..models.event import TaskEvent, TaskEventType
from .base import BaseQueue

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Manages task dependencies and determines when tasks are ready to run.
    
    This resolver maintains a dependency graph of tasks and tracks the
    completion status of dependencies to determine when dependent tasks
    can be enqueued for execution.
    """
    
    def __init__(self, result_storage: Any, event_storage: Optional[Any] = None):
        """Initialize DependencyResolver.
        
        Args:
            result_storage: Result storage to check task completion status
            event_storage: Event storage for logging dependency events (optional)
        """
        self.result_storage = result_storage
        self.event_storage = event_storage
        
        # Dependency tracking
        self._dependency_graph: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        self._reverse_graph: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        self._pending_tasks: Dict[uuid.UUID, Task] = {}
        self._completed_tasks: Set[uuid.UUID] = set()
        self._failed_tasks: Set[uuid.UUID] = set()
    
    async def add_task_with_dependencies(
        self,
        task: Task,
        task_queue: BaseQueue,
        queue_name: str = "default"
    ) -> bool:
        """Add a task with its dependencies.
        
        This method adds a task to the dependency resolver and enqueues it
        immediately if all dependencies are satisfied, or holds it until
        dependencies are met.
        
        Args:
            task: The task to add
            task_queue: Task queue to enqueue to when ready
            queue_name: Name of the queue to enqueue to
            
        Returns:
            True if task was enqueued immediately, False if waiting for dependencies
        """
        # Store the task
        self._pending_tasks[task.id] = task
        
        # Build dependency graph
        if task.dependencies:
            self._dependency_graph[task.id] = set(task.dependencies)
            
            # Build reverse graph for efficient lookup
            for dep_id in task.dependencies:
                if dep_id not in self._reverse_graph:
                    self._reverse_graph[dep_id] = set()
                self._reverse_graph[dep_id].add(task.id)
        
        # Check if task can be enqueued immediately
        if await self._are_dependencies_satisfied(task.id):
            await self._enqueue_task(task.id, task_queue, queue_name)
            return True
        
        # Log dependency wait event if event storage is available
        if self.event_storage is not None:
            event = TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.DEPENDENCY_WAIT,
                timestamp=datetime.utcnow(),
                metadata={"dependencies": task.dependencies}
            )
            await self.event_storage.log_event_async(event)
        
        logger.info(f"Task {task.id} waiting for dependencies: {task.dependencies}")
        return False
    
    async def mark_task_completed(self, task_id: uuid.UUID, task_queue: BaseQueue) -> List[uuid.UUID]:
        """Mark a task as completed and check for dependent tasks.
        
        This method should be called when a task completes successfully.
        It will check if any dependent tasks can now be enqueued.
        
        Args:
            task_id: ID of the completed task
            task_queue: Task queue to enqueue dependent tasks to
            
        Returns:
            List of task IDs that were enqueued as a result
        """
        if task_id in self._completed_tasks:
            return []
        
        # Mark task as completed
        self._completed_tasks.add(task_id)
        
        # Remove from pending tasks if it exists
        self._pending_tasks.pop(task_id, None)
        
        # Remove from failed tasks if it was there
        self._failed_tasks.discard(task_id)
        
        # Check for dependent tasks that can now run
        enqueued_tasks = []
        
        if task_id in self._reverse_graph:
            dependent_tasks = list(self._reverse_graph[task_id])
            
            for dependent_id in dependent_tasks:
                if await self._are_dependencies_satisfied(dependent_id):
                    if dependent_id in self._pending_tasks:
                        dependent_task = self._pending_tasks[dependent_id]
                        queue_name = getattr(dependent_task, 'queue_name', 'default')
                        await self._enqueue_task(dependent_id, task_queue, queue_name)
                        enqueued_tasks.append(dependent_id)
        
        logger.info(f"Task {task_id} completed, enqueued {len(enqueued_tasks)} dependent tasks")
        return enqueued_tasks
    
    async def mark_task_failed(self, task_id: uuid.UUID) -> List[uuid.UUID]:
        """Mark a task as failed and notify dependent tasks.
        
        This method should be called when a task fails.
        It will notify all dependent tasks that one of their dependencies failed.
        
        Args:
            task_id: ID of the failed task
            
        Returns:
            List of task IDs that were affected by the failure
        """
        if task_id in self._failed_tasks:
            return []
        
        # Mark task as failed
        self._failed_tasks.add(task_id)
        
        # Remove from pending tasks if it exists
        self._pending_tasks.pop(task_id, None)
        
        # Remove from completed tasks if it was there
        self._completed_tasks.discard(task_id)
        
        # Notify dependent tasks
        affected_tasks = []
        
        if task_id in self._reverse_graph:
            dependent_tasks = list(self._reverse_graph[task_id])
            
            for dependent_id in dependent_tasks:
                # Remove the failed dependency from the graph
                if dependent_id in self._dependency_graph:
                    self._dependency_graph[dependent_id].discard(task_id)
                
                # Log dependency failure event if event storage is available
                if self.event_storage is not None and dependent_id in self._pending_tasks:
                    event = TaskEvent(
                        task_id=dependent_id,
                        event_type=TaskEventType.DEPENDENCY_FAILED,
                        timestamp=datetime.utcnow(),
                        metadata={"failed_dependency": str(task_id)}
                    )
                    await self.event_storage.log_event_async(event)
                
                affected_tasks.append(dependent_id)
        
        logger.warning(f"Task {task_id} failed, affected {len(affected_tasks)} dependent tasks")
        return affected_tasks
    
    async def get_pending_tasks(self) -> List[Task]:
        """Get all tasks that are waiting for dependencies.
        
        Returns:
            List of pending tasks
        """
        return list(self._pending_tasks.values())
    
    async def get_task_dependencies(self, task_id: uuid.UUID) -> List[uuid.UUID]:
        """Get the dependencies for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            List of dependency task IDs
        """
        return list(self._dependency_graph.get(task_id, set()))
    
    async def get_dependent_tasks(self, task_id: uuid.UUID) -> List[uuid.UUID]:
        """Get tasks that depend on the given task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            List of dependent task IDs
        """
        return list(self._reverse_graph.get(task_id, set()))
    
    async def is_task_ready(self, task_id: uuid.UUID) -> bool:
        """Check if a task is ready to run (all dependencies satisfied).
        
        Args:
            task_id: ID of the task
            
        Returns:
            True if task is ready, False otherwise
        """
        return await self._are_dependencies_satisfied(task_id)
    
    async def remove_task(self, task_id: uuid.UUID) -> None:
        """Remove a task from the dependency resolver.
        
        This cleans up all dependency relationships for the task.
        
        Args:
            task_id: ID of the task to remove
        """
        # Remove from pending tasks
        self._pending_tasks.pop(task_id, None)
        
        # Remove from completed/failed sets
        self._completed_tasks.discard(task_id)
        self._failed_tasks.discard(task_id)
        
        # Remove from dependency graph
        if task_id in self._dependency_graph:
            dependencies = self._dependency_graph[task_id]
            
            # Remove from reverse graph
            for dep_id in dependencies:
                if dep_id in self._reverse_graph:
                    self._reverse_graph[dep_id].discard(task_id)
                    if not self._reverse_graph[dep_id]:
                        del self._reverse_graph[dep_id]
            
            del self._dependency_graph[task_id]
        
        # Remove from reverse graph
        if task_id in self._reverse_graph:
            dependent_tasks = self._reverse_graph[task_id]
            
            for dep_id in dependent_tasks:
                if dep_id in self._dependency_graph:
                    self._dependency_graph[dep_id].discard(task_id)
                    if not self._dependency_graph[dep_id]:
                        del self._dependency_graph[dep_id]
            
            del self._reverse_graph[task_id]
        
        logger.info(f"Removed task {task_id} from dependency resolver")
    
    async def _are_dependencies_satisfied(self, task_id: uuid.UUID) -> bool:
        """Check if all dependencies for a task are satisfied.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        if task_id not in self._dependency_graph:
            return True
        
        dependencies = self._dependency_graph[task_id]
        
        for dep_id in dependencies:
            # Check if dependency is completed
            if dep_id not in self._completed_tasks:
                # If not in completed set, check result storage
                if self.result_storage is not None:
                    result = await self.result_storage.get_result_async(dep_id)
                    if result is None or result.status != TaskStatus.COMPLETED:
                        return False
                else:
                    # No result storage, can't verify completion
                    return False
        
        return True
    
    async def _enqueue_task(
        self,
        task_id: uuid.UUID,
        task_queue: BaseQueue,
        queue_name: str = "default"
    ) -> None:
        """Enqueue a task that is ready to run.
        
        Args:
            task_id: ID of the task to enqueue
            task_queue: Task queue to enqueue to
            queue_name: Name of the queue to enqueue to
        """
        if task_id not in self._pending_tasks:
            logger.warning(f"Task {task_id} not found in pending tasks")
            return
        
        task = self._pending_tasks[task_id]
        
        # Enqueue the task
        await task_queue.enqueue_async(task, queue_name)
        
        # Remove from pending tasks
        del self._pending_tasks[task_id]
        
        # Remove from dependency graph
        self._dependency_graph.pop(task_id, None)
        
        # Log dependency satisfied event if event storage is available
        if self.event_storage is not None:
            event = TaskEvent(
                task_id=task_id,
                event_type=TaskEventType.DEPENDENCY_SATISFIED,
                timestamp=datetime.utcnow()
            )
            await self.event_storage.log_event_async(event)
        
        logger.info(f"Enqueued task {task_id} with satisfied dependencies")
    
    async def get_dependency_graph(self) -> Dict[uuid.UUID, List[uuid.UUID]]:
        """Get the current dependency graph.
        
        Returns:
            Dictionary mapping task IDs to their dependencies
        """
        return {
            task_id: list(deps)
            for task_id, deps in self._dependency_graph.items()
        }
    
    async def get_stats(self) -> Dict[str, int]:
        """Get dependency resolver statistics.
        
        Returns:
            Dictionary with statistics about the resolver state
        """
        return {
            "pending_tasks": len(self._pending_tasks),
            "completed_tasks": len(self._completed_tasks),
            "failed_tasks": len(self._failed_tasks),
            "dependency_graph_size": len(self._dependency_graph),
            "reverse_graph_size": len(self._reverse_graph)
        }