"""OmniQ Workers - Task execution engines with multiple execution models."""

from .base import BaseWorker, WorkerState
from .async_ import AsyncWorker
from .thread import ThreadWorker
from .process import ProcessWorker

# Optional gevent worker
try:
    from .gevent import GeventWorker
    _GEVENT_AVAILABLE = True
except ImportError:
    _GEVENT_AVAILABLE = False

__all__ = [
    "BaseWorker",
    "WorkerState",
    "AsyncWorker",
    "ThreadWorker", 
    "ProcessWorker",
]

if _GEVENT_AVAILABLE:
    __all__.append("GeventWorker")