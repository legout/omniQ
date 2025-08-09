import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"         # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if the system has recovered


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    This pattern protects against repeated failures by temporarily blocking
    requests to a failing service and allowing it to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Optional[List[type]] = None,
        timeout: Optional[float] = None
    ):
        """
        Initialize the CircuitBreaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: List of exception types that should be counted as failures
            timeout: Timeout in seconds for circuit breaker operations
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception or [Exception]
        self.timeout = timeout
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0
        self._success_threshold = 3  # Successes needed to close circuit from half-open
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
            
        Raises:
            The original exception if the call fails
            CircuitBreakerOpenError if the circuit is open
        """
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker is OPEN - blocking calls to {func.__name__}")
        
        try:
            if self.timeout:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
            else:
                result = await func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except tuple(self.expected_exception) as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt resetting the circuit.
        
        Returns:
            True if the circuit should attempt to reset, False otherwise
        """
        if self._last_failure_time is None:
            return False
            
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle a successful call."""
        self._failure_count = 0
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                self._state = CircuitState.CLOSED
                self._success_count = 0
                logger.info("Circuit breaker transitioned to CLOSED state")
        else:
            # In CLOSED state, just reset success count
            self._success_count = 0
    
    def _on_failure(self) -> None:
        """Handle a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._success_count = 0
        
        if self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN immediately opens the circuit
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker transitioned to OPEN state after {self._failure_count} failures")
        elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            # Too many failures in CLOSED state opens the circuit
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker transitioned to OPEN state after {self._failure_count} failures")
    
    def get_state(self) -> CircuitState:
        """Get the current state of the circuit breaker."""
        return self._state
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the circuit breaker state.
        
        Returns:
            Dictionary containing circuit breaker statistics
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "time_since_failure": (
                time.time() - self._last_failure_time
                if self._last_failure_time else None
            )
        }
    
    def force_open(self) -> None:
        """Force the circuit breaker into the OPEN state."""
        self._state = CircuitState.OPEN
        logger.info("Circuit breaker forced to OPEN state")
    
    def force_close(self) -> None:
        """Force the circuit breaker into the CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit breaker forced to CLOSED state")
    
    def reset(self) -> None:
        """Reset the circuit breaker to its initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info("Circuit breaker reset to initial state")


class CircuitBreakerOpenError(Exception):
    """Exception raised when the circuit breaker is open."""
    pass


class CircuitBreakerDecorator:
    """
    Decorator for applying circuit breaker protection to functions.
    """
    
    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Optional[List[type]] = None,
        timeout: Optional[float] = None
    ):
        """
        Initialize the decorator.
        
        Args:
            circuit_breaker: Existing CircuitBreaker instance to use
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: List of exception types that should be counted as failures
            timeout: Timeout in seconds for circuit breaker operations
        """
        if circuit_breaker is None:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                timeout=timeout
            )
        else:
            self.circuit_breaker = circuit_breaker
    
    def __call__(self, func: Callable) -> Callable:
        """Apply the circuit breaker to the function."""
        async def wrapper(*args, **kwargs):
            return await self.circuit_breaker.call(func, *args, **kwargs)
        return wrapper