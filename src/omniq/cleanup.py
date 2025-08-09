"""Cleanup mechanisms for OmniQ.

This module provides periodic cleanup mechanisms for expired tasks and results
across all storage backends.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .queue.base import BaseQueue
from .results.base import BaseResultStorage
from .events.base import BaseEventStorage


logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages periodic cleanup of expired tasks and results.
    
    This class provides a centralized mechanism for cleaning up expired
    tasks and results across all storage backends with configurable
    intervals and strategies.
    """
    
    def __init__(
        self,
        queue: Optional[BaseQueue] = None,
        result_storage: Optional[BaseResultStorage] = None,
        event_storage: Optional[BaseEventStorage] = None,
        cleanup_interval: float = 3600.0,  # 1 hour default
        task_cleanup_enabled: bool = True,
        result_cleanup_enabled: bool = True,
        event_cleanup_enabled: bool = True
    ):
        """Initialize the cleanup manager.
        
        Args:
            queue: Task queue to clean up
            result_storage: Result storage to clean up
            event_storage: Event storage to clean up
            cleanup_interval: Interval between cleanup runs in seconds
            task_cleanup_enabled: Whether to clean up expired tasks
            result_cleanup_enabled: Whether to clean up expired results
            event_cleanup_enabled: Whether to clean up expired events
        """
        self.queue = queue
        self.result_storage = result_storage
        self.event_storage = event_storage
        self.cleanup_interval = cleanup_interval
        self.task_cleanup_enabled = task_cleanup_enabled
        self.result_cleanup_enabled = result_cleanup_enabled
        self.event_cleanup_enabled = event_cleanup_enabled
        
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the periodic cleanup process."""
        if self._running:
            logger.warning("Cleanup manager is already running")
            return
        
        self._running = True
        logger.info("Starting cleanup manager")
        
        # Start the cleanup loop
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop the periodic cleanup process."""
        if not self._running:
            return
        
        logger.info("Stopping cleanup manager")
        self._running = False
        
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        logger.info("Cleanup manager stopped")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while self._running:
            try:
                # Run cleanup
                await self.run_cleanup()
                
                # Wait for next cleanup cycle
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                # Wait before retrying
                await asyncio.sleep(60)  # 1 minute delay on error
    
    async def run_cleanup(self) -> Dict[str, int]:
        """Run a single cleanup cycle.
        
        Returns:
            Dictionary with cleanup counts for each component
        """
        logger.info("Starting cleanup cycle")
        
        results = {
            "tasks_cleaned": 0,
            "results_cleaned": 0,
            "events_cleaned": 0
        }
        
        # Clean up expired tasks
        if self.task_cleanup_enabled and self.queue is not None:
            try:
                # Check if queue has cleanup method
                if hasattr(self.queue, 'cleanup_expired_tasks_async'):
                    tasks_cleaned = await self.queue.cleanup_expired_tasks_async()
                    results["tasks_cleaned"] = tasks_cleaned
                    logger.info(f"Cleaned up {tasks_cleaned} expired tasks")
            except Exception as e:
                logger.error(f"Error cleaning up tasks: {e}", exc_info=True)
        
        # Clean up expired results
        if self.result_cleanup_enabled and self.result_storage is not None:
            try:
                results_cleaned = await self.result_storage.cleanup_expired_async()
                results["results_cleaned"] = results_cleaned
                logger.info(f"Cleaned up {results_cleaned} expired results")
            except Exception as e:
                logger.error(f"Error cleaning up results: {e}", exc_info=True)
        
        # Clean up expired events
        if self.event_cleanup_enabled and self.event_storage is not None:
            try:
                # Check if event storage has cleanup method
                if hasattr(self.event_storage, 'cleanup_old_events_async'):
                    events_cleaned = await self.event_storage.cleanup_old_events_async()
                    results["events_cleaned"] = events_cleaned
                    logger.info(f"Cleaned up {events_cleaned} expired events")
            except Exception as e:
                logger.error(f"Error cleaning up events: {e}", exc_info=True)
        
        logger.info(f"Cleanup cycle completed: {results}")
        return results
    
    async def run_cleanup_now(self) -> Dict[str, int]:
        """Run cleanup immediately without waiting for the next scheduled cycle.
        
        Returns:
            Dictionary with cleanup counts for each component
        """
        return await self.run_cleanup()
    
    def is_running(self) -> bool:
        """Check if the cleanup manager is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running
    
    async def __aenter__(self) -> "CleanupManager":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()