# src/omniq/storage/memory.py
"""Memory storage implementations for OmniQ."""

import os
import json
import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from fsspec.implementations.memory import MemoryFileSystem

from omniq.models.result import TaskResult
from omniq.models.event import TaskEvent
from omniq.storage.base import BaseResultStorage, BaseEventStorage
from omniq.serialization.manager import SerializationManager

class MemoryResultStorage(BaseResultStorage):
    """Result storage implementation using fsspec MemoryFileSystem."""
    
    def __init__(
        self, 
        project_name: str, 
        fs = None,
        serialization_manager: SerializationManager = None,
        **kwargs
    ):
        """
        Initialize a memory result storage.
        
        Args:
            project_name: Name of the project
            fs: MemoryFileSystem instance
            serialization_manager: Serialization manager for results
        """
        self.project_name = project_name
        self.serialization_manager = serialization_manager or SerializationManager()
        
        # Create file system if not provided
        self.fs = fs or MemoryFileSystem()
        
        # Create results directory
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize results directory."""
        results_path = os.path.join(self.project_name, "results")
        self.fs.makedirs(results_path, exist_ok=True)
    
    def _get_result_path(self, task_id: str) -> str:
        """Get the path for a result."""
        return os.path.join(self.project_name, "results", f"{task_id}.result")
    
    def _get_metadata_path(self, task_id: str) -> str:
        """Get the path for result metadata."""
        return os.path.join(self.project_name, "results", f"{task_id}.meta")
    
    # Implementation follows the same pattern as FileResultStorage
    # but uses self.fs for file operations
    
    def store(
        self, 
        task_id: str, 
        result: Any, 
        status: str = "success", 
        error: Optional[str] = None, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Store a task result.
        
        Args:
            task_id: Task ID
            result: Result data
            status: Result status
            error: Error message
            ttl: Time-to-live for the result
            
        Returns:
            True if successful
        """
        # Create result object
        task_result = TaskResult.create(
            task_id=task_id,
            result=result,
            status=status,
            error=error,
            ttl=ttl
        )
        
        # Serialize result
        result_data = self.serialization_manager.serialize(task_result)
        
        # Create metadata
        metadata = {
            "task_id": task_id,
            "status": status,
            "created_at": task_result.created_at.isoformat(),
            "expires_at": task_result.expires_at.isoformat() if task_result.expires_at else None
        }
        
        # Write result and metadata
        result_path = self._get_result_path(task_id)
        metadata_path = self._get_metadata_path(task_id)
        
        try:
            with self.fs.open(result_path, 'wb') as f:
                f.write(result_data)
            
            with self.fs.open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            return True
        except Exception:
            return False
    
    def get(self, task_id: str, keep: bool = True) -> Optional[Any]:
        """
        Get a task result.
        
        Args:
            task_id: Task ID
            keep: Whether to keep the result after retrieval
            
        Returns:
            Result data or None if not found
        """
        result_path = self._get_result_path(task_id)
        metadata_path = self._get_metadata_path(task_id)
        
        if not self.fs.exists(result_path) or not self.fs.exists(metadata_path):
            return None
        
        try:
            # Read metadata
            with self.fs.open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if result is expired
            now = datetime.utcnow()
            if metadata['expires_at']:
                expires_at = datetime.fromisoformat(metadata['expires_at'])
                if expires_at <= now:
                    # Result expired
                    if self.fs.exists(result_path):
                        self.fs.rm(result_path)
                    if self.fs.exists(metadata_path):
                        self.fs.rm(metadata_path)
                    return None
            
            # Read result
            with self.fs.open(result_path, 'rb') as f:
                result_data = f.read()
            
            # Deserialize result
            task_result = self.serialization_manager.deserialize(result_data)
            
            # Remove result if not keeping
            if not keep:
                if self.fs.exists(result_path):
                    self.fs.rm(result_path)
                if self.fs.exists(metadata_path):
                    self.fs.rm(metadata_path)
            
            return task_result.result
        except Exception:
            return None

class MemoryEventStorage(BaseEventStorage):
    """Event storage implementation using fsspec MemoryFileSystem."""
    
    def __init__(
        self, 
        project_name: str, 
        fs = None,
        **kwargs
    ):
        """
        Initialize a memory event storage.
        
        Args:
            project_name: Name of the project
            fs: MemoryFileSystem instance
        """
        self.project_name = project_name
        
        # Create file system if not provided
        self.fs = fs or MemoryFileSystem()
        
        # Create events directory
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize events directory."""
        events_path = os.path.join(self.project_name, "events")
        self.fs.makedirs(events_path, exist_ok=True)
    
    def _get_event_path(self, task_id: str, event_type: str) -> str:
        """Get the path for an event."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return os.path.join(
            self.project_name, 
            "events", 
            f"{task_id}_{event_type}_{timestamp}_{event_id}.json"
        )
    
    # Implementation follows the same pattern as FileEventStorage
    # but uses self.fs for file operations
    
    def log(
        self, 
        task_id: str, 
        event_type: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a task event.
        
        Args:
            task_id: Task ID
            event_type: Event type
            data: Event data
            
        Returns:
            True if successful
        """
        # Create event object
        event = TaskEvent.create(
            task_id=task_id,
            event_type=event_type,
            data=data
        )
        
        # Convert event to JSON
        event_json = {
            "task_id": task_id,
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }
        
        # Write event
        event_path = self._get_event_path(task_id, event_type)
        
        try:
            with self.fs.open(event_path, 'w') as f:
                json.dump(event_json, f)
            return True
        except Exception:
            return False
    
    def get_events(
        self, 
        task_id: Optional[str] = None, 
        event_type: Optional[str] = None, 
        start: Optional[datetime] = None, 
        end: Optional[datetime] = None
    ) -> List[TaskEvent]:
        """
        Get task events.
        
        Args:
            task_id: Filter by task ID
            event_type: Filter by event type
            start: Filter by start time
            end: Filter by end time
            
        Returns:
            List of events
        """
        events_path = os.path.join(self.project_name, "events")
        
        if not self.fs.exists(events_path):
            return []
        
        events = []
        
        # List all event files
        try:
            event_files = self.fs.find(events_path, maxdepth=1)
            event_files = [f for f in event_files if f.endswith('.json')]
        except Exception:
            return []
        
        for event_file in event_files:
            # Filter by task ID
            if task_id and not os.path.basename(event_file).startswith(f"{task_id}_"):
                continue
            
            # Filter by event type
            if event_type and f"_{event_type}_" not in os.path.basename(event_file):
                continue
            
            try:
                # Read event
                with self.fs.open(event_file, 'r') as f:
                    event_data = json.load(f)
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(event_data['timestamp'])
                
                # Filter by time range
                if start and timestamp < start:
                    continue
                if end and timestamp > end:
                    continue
                
                # Create event object
                event = TaskEvent(
                    task_id=event_data['task_id'],
                    event_type=event_data['event_type'],
                    timestamp=timestamp,
                    data=event_data['data']
                )
                
                events.append(event)
            except Exception:
                # Skip invalid events
                continue
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events