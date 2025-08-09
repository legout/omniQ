"""Memory result storage implementations for OmniQ.

This module provides concrete memory-based implementations of the result storage interface:
- AsyncMemoryResultStorage and MemoryResultStorage: Result storage with TTL support using fsspec.MemoryFileSystem

All implementations follow the "Async First, Sync Wrapped" principle.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, AsyncIterator, Iterator

import anyio
import fsspec
import msgspec
from fsspec.implementations.memory import MemoryFileSystem

from .base import BaseResultStorage
from ..models.result import TaskResult, TaskStatus


class AsyncMemoryResultStorage(BaseResultStorage):
    """Async memory-based result storage implementation.
    
    Features:
    - TTL support with automatic cleanup
    - Status-based querying
    - Volatile storage (data lost on restart)
    - Fast in-memory operations
    """
    
    def __init__(self):
        """Initialize the async memory result storage."""
        self.fs = MemoryFileSystem()
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the filesystem and directories are initialized."""
        if self._initialized:
            return
        
        # Ensure results directory exists
        self.fs.makedirs("results", exist_ok=True)
        
        self._initialized = True
    
    def _get_result_path(self, task_id: uuid.UUID) -> str:
        """Get the path for a specific result."""
        return f"results/{task_id}.json"
    
    async def store_result_async(self, result: TaskResult) -> None:
        """Store a task result asynchronously."""
        await self._ensure_initialized()
        
        result_path = self._get_result_path(result.task_id)
        
        # Calculate expiration time
        expires_at = None
        if result.ttl:
            expires_at = (result.timestamp + result.ttl).isoformat()
        
        # Serialize result data
        result_data = {
            "task_id": str(result.task_id),
            "status": result.status.value,
            "result_data": result.result_data,
            "timestamp": result.timestamp.isoformat(),
            "expires_at": expires_at
        }
        
        # Write result file
        with self.fs.open(result_path, "w") as f:
            msgspec.json.dump(result_data, f)
    
    async def get_result_async(self, task_id: uuid.UUID) -> Optional[TaskResult]:
        """Retrieve a task result asynchronously."""
        await self._ensure_initialized()
        
        result_path = self._get_result_path(task_id)
        
        try:
            with self.fs.open(result_path, "r") as f:
                result_data = msgspec.json.load(f)
            
            # Check if result has expired
            if result_data.get("expires_at"):
                expires_at = datetime.fromisoformat(result_data["expires_at"])
                if datetime.utcnow() > expires_at:
                    # Clean up expired result
                    self.fs.rm(result_path)
                    return None
            
            # Reconstruct the result
            timestamp = datetime.fromisoformat(result_data["timestamp"])
            status = TaskStatus(result_data["status"])
            
            # Calculate TTL
            ttl = None
            if result_data.get("expires_at"):
                expires_at = datetime.fromisoformat(result_data["expires_at"])
                ttl = expires_at - timestamp
            
            return TaskResult(
                task_id=task_id,
                status=status,
                result_data=result_data["result_data"],
                timestamp=timestamp,
                ttl=ttl
            )
            
        except FileNotFoundError:
            return None
        except Exception:
            # Handle corrupted result files
            return None
    
    async def delete_result_async(self, task_id: uuid.UUID) -> bool:
        """Delete a task result asynchronously."""
        await self._ensure_initialized()
        
        result_path = self._get_result_path(task_id)
        
        try:
            self.fs.rm(result_path)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results asynchronously."""
        await self._ensure_initialized()
        
        count = 0
        now = datetime.utcnow()
        
        try:
            for result_file in self.fs.glob("results/*.json"):
                try:
                    with self.fs.open(result_file, "r") as f:
                        result_data = msgspec.json.load(f)
                    
                    if result_data.get("expires_at"):
                        expires_at = datetime.fromisoformat(result_data["expires_at"])
                        if now > expires_at:
                            self.fs.rm(result_file)
                            count += 1
                except Exception:
                    # Skip corrupted result files
                    continue
        except Exception:
            pass
        
        return count
    
    async def get_results_by_status_async(self, status: str) -> AsyncIterator[TaskResult]:
        """Get all results with a specific status asynchronously."""
        await self._ensure_initialized()
        
        now = datetime.utcnow()
        
        try:
            # Get all result files
            result_files = self.fs.glob("results/*.json")
            
            # Sort by timestamp (newest first)
            result_files.sort(key=lambda f: self.fs.info(f)["created"], reverse=True)
            
            for result_file in result_files:
                try:
                    with self.fs.open(result_file, "r") as f:
                        result_data = msgspec.json.load(f)
                    
                    # Check if result has expired
                    if result_data.get("expires_at"):
                        expires_at = datetime.fromisoformat(result_data["expires_at"])
                        if now > expires_at:
                            continue
                    
                    # Check status match
                    if result_data.get("status") == status:
                        # Reconstruct the result
                        task_id = uuid.UUID(result_data["task_id"])
                        timestamp = datetime.fromisoformat(result_data["timestamp"])
                        task_status = TaskStatus(result_data["status"])
                        
                        # Calculate TTL
                        ttl = None
                        if result_data.get("expires_at"):
                            expires_at = datetime.fromisoformat(result_data["expires_at"])
                            ttl = expires_at - timestamp
                        
                        yield TaskResult(
                            task_id=task_id,
                            status=task_status,
                            result_data=result_data["result_data"],
                            timestamp=timestamp,
                            ttl=ttl
                        )
                except Exception:
                    # Skip corrupted result files
                    continue
                    
        except Exception:
            pass


class MemoryResultStorage(AsyncMemoryResultStorage):
    """Synchronous wrapper for AsyncMemoryResultStorage."""
    
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