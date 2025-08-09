"""NATS result storage implementations for OmniQ.

This module provides concrete NATS-based implementations of the result storage interface:
- AsyncNATSResultStorage and NATSResultStorage: Result storage using nats.aio

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, AsyncIterator, Iterator, Dict, Any

import anyio
import nats.aio.client
import msgspec

from .base import BaseResultStorage
from ..models.result import TaskResult, TaskStatus


class AsyncNATSResultStorage(BaseResultStorage):
    """Async NATS-based result storage implementation.
    
    Features:
    - Distributed result storage with NATS
    - Request-reply pattern for result retrieval
    - Persistent storage with JetStream (if available)
    """
    
    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        subject_prefix: str = "omniq",
        **connection_kwargs
    ):
        """Initialize the async NATS result storage.
        
        Args:
            nats_url: NATS connection URL
            subject_prefix: Prefix for all NATS subjects
            **connection_kwargs: Additional connection arguments for NATS
        """
        self.nats_url = nats_url
        self.subject_prefix = subject_prefix
        self.connection_kwargs = connection_kwargs
        self.nc: Optional[nats.aio.client.Client] = None
        self.js: Optional[nats.aio.client.JetStream] = None
        self._initialized = False
        self._results: Dict[uuid.UUID, TaskResult] = {}
        self._subscriptions: Dict[str, nats.aio.client.Subscription] = {}
    
    async def _ensure_initialized(self):
        """Ensure the NATS connection is initialized."""
        if self._initialized:
            return
        
        # Create NATS connection
        self.nc = await nats.aio.client.connect(
            self.nats_url,
            **self.connection_kwargs
        )
        
        # Try to get JetStream context
        try:
            self.js = self.nc.jetstream()
        except Exception:
            # JetStream not available, will use basic NATS
            pass
        
        self._initialized = True
    
    def _get_result_subject(self, task_id: uuid.UUID) -> str:
        """Get the NATS subject for a specific result."""
        return f"{self.subject_prefix}.result.{task_id}"
    
    def _get_status_subject(self, status: str) -> str:
        """Get the NATS subject for a status."""
        return f"{self.subject_prefix}.status.{status}"
    
    def _get_request_subject(self, task_id: uuid.UUID) -> str:
        """Get the NATS subject for result requests."""
        return f"{self.subject_prefix}.request.{task_id}"
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        # Store result in memory
        self._results[result.task_id] = result
        
        # Serialize result data
        result_data = {
            "task_id": str(result.task_id),
            "status": result.status.value,
            "result_data": msgspec.json.encode(result.result_data),
            "timestamp": result.timestamp.isoformat(),
            "ttl_seconds": int(result.ttl.total_seconds()) if result.ttl else None
        }
        
        # Publish result to NATS
        result_subject = self._get_result_subject(result.task_id)
        status_subject = self._get_status_subject(result.status.value)
        
        if self.js:
            # Use JetStream for persistent messaging
            try:
                await self.js.publish(result_subject, json.dumps(result_data).encode())
                await self.js.publish(status_subject, str(result.task_id).encode())
            except Exception:
                # Fall back to basic NATS
                await self.nc.publish(result_subject, json.dumps(result_data).encode())
                await self.nc.publish(status_subject, str(result.task_id).encode())
        else:
            # Use basic NATS
            await self.nc.publish(result_subject, json.dumps(result_data).encode())
            await self.nc.publish(status_subject, str(result.task_id).encode())
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        # Check if result is in memory
        if task_id in self._results:
            result = self._results[task_id]
            
            # Check if result has expired
            if result.ttl and (datetime.utcnow() - result.timestamp) > result.ttl:
                # Clean up expired result
                del self._results[task_id]
                return None
            
            return result
        
        # Try to fetch result from NATS
        request_subject = self._get_request_subject(task_id)
        result_subject = self._get_result_subject(task_id)
        
        # Create a subscription for the result
        sub = await self.nc.subscribe(result_subject)
        
        try:
            # Send request for result
            await self.nc.publish(request_subject, b"")
            
            # Wait for response with timeout
            msg = await sub.next_msg(timeout=5.0)
            
            if msg:
                # Parse result data
                result_data = json.loads(msg.data.decode())
                
                # Reconstruct the result
                result_data_decoded = msgspec.json.decode(result_data["result_data"]) if result_data["result_data"] else None
                timestamp = datetime.fromisoformat(result_data["timestamp"])
                status = TaskStatus(result_data["status"])
                
                # Calculate TTL
                ttl = None
                if result_data["ttl_seconds"]:
                    ttl = timedelta(seconds=result_data["ttl_seconds"])
                
                result = TaskResult(
                    task_id=task_id,
                    status=status,
                    result_data=result_data_decoded,
                    timestamp=timestamp,
                    ttl=ttl
                )
                
                # Store result in memory
                self._results[task_id] = result
                
                return result
            
            return None
        except asyncio.TimeoutError:
            return None
        finally:
            # Clean up subscription
            try:
                await sub.unsubscribe()
            except Exception:
                pass
    
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously."""
        await self._ensure_initialized()
        
        # Remove from memory
        if task_id in self._results:
            del self._results[task_id]
            return True
        
        return False
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        await self._ensure_initialized()
        
        count = 0
        expired_results = []
        
        # Find expired results
        for task_id, result in self._results.items():
            if result.ttl and (datetime.utcnow() - result.timestamp) > result.ttl:
                expired_results.append(task_id)
        
        # Remove expired results
        for task_id in expired_results:
            del self._results[task_id]
            count += 1
        
        return count
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        # Subscribe to status subject
        status_subject = self._get_status_subject(status)
        sub = await self.nc.subscribe(status_subject)
        
        try:
            # Wait for messages with timeout
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            
            while True:
                remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining_time <= 0:
                    break
                
                try:
                    msg = await sub.next_msg(timeout=remaining_time)
                    
                    if msg:
                        # Parse task ID
                        task_id_str = msg.data.decode()
                        task_id = uuid.UUID(task_id_str)
                        
                        # Get result
                        result = await self.get_result_async(task_id)
                        
                        if result and result.status.value == status:
                            yield result
                except asyncio.TimeoutError:
                    break
        finally:
            # Clean up subscription
            try:
                await sub.unsubscribe()
            except Exception:
                pass
    
    async def close_async(self) -> None:
        """Close the NATS connection."""
        # Clean up subscriptions
        for sub in self._subscriptions.values():
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        
        self._subscriptions.clear()
        
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
            self._initialized = False
            self._results.clear()


class NATSResultStorage(AsyncNATSResultStorage):
    """Synchronous wrapper for AsyncNATSResultStorage."""
    
    def store_result(self, result: TaskResult) -> None:
        """Synchronous wrapper for store_result_async."""
        anyio.run(self.store_result_async, result)
    
    def get_result(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Synchronous wrapper for get_result_async."""
        return anyio.run(self.get_result_async, task_id)
    
    def delete_result(self, task_id: uuid.UUID) -> bool:
        """Synchronous wrapper for delete_result_async."""
        return anyio.run(self.delete_result_async, task_id)
    
    def cleanup_expired(self) -> int:
        """Synchronous wrapper for cleanup_expired_async."""
        return anyio.run(self.cleanup_expired_async)
    
    def get_results_by_status(self, status: str) -> Iterator[TaskResult]:
        """Synchronous wrapper for get_results_by_status_async."""
        async def _collect_results():
            results = []
            async for result in self.get_results_by_status_async(status):
                results.append(result)
            return results
        
        # Convert async generator to sync iterator
        results = anyio.run(_collect_results)
        return iter(results)
    
    def close(self) -> None:
        """Synchronous wrapper for close_async."""
        anyio.run(self.close_async)
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()