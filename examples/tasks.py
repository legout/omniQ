"""Shared task functions for OmniQ examples.

All tasks are top-level functions for stable func_path resolution.
"""

import asyncio
from typing import Any


def sync_add(a: int, b: int) -> int:
    """Simple synchronous addition task."""
    result = a + b
    print(f"  sync_add({a}, {b}) = {result}")
    return result


async def async_multiply(a: int, b: int) -> int:
    """Simple asynchronous multiplication task."""
    await asyncio.sleep(0.001)  # Tiny async yield
    result = a * b
    print(f"  async_multiply({a}, {b}) = {result}")
    return result


_task_call_counts: dict[str, int] = {}


def flaky_task(value: Any, fail_before: int = 2) -> str:
    """Deterministic task that fails a set number of times before succeeding.

    Args:
        value: Any value to be echoed back
        fail_before: Number of times to fail before succeeding (default: 2)

    Returns:
        The value with success message

    Raises:
        RuntimeError: Until the task has been called fail_before times
    """
    task_name = f"flaky_task_{value}"

    if task_name not in _task_call_counts:
        _task_call_counts[task_name] = 0

    _task_call_counts[task_name] += 1
    attempt = _task_call_counts[task_name]

    if attempt <= fail_before:
        print(
            f"  flaky_task({value}) - Attempt {attempt}: FAILING (will fail {fail_before} times)"
        )
        raise RuntimeError(f"Simulated failure (attempt {attempt}/{fail_before})")

    print(f"  flaky_task({value}) - Attempt {attempt}: SUCCESS")
    return f"Success: {value}"


def echo_task(value: Any) -> str:
    """Simple task that echoes its input."""
    print(f"  echo_task({value})")
    return f"Echo: {value}"


def process_item(item_id: int, data: str) -> dict:
    """Task that processes an item and returns a result dict."""
    print(f"  process_item(item_id={item_id}, data={data})")
    return {"item_id": item_id, "status": "processed", "data": data}


def reset_call_counts():
    """Reset call count tracker for flaky_task (useful for testing)."""
    global _task_call_counts
    _task_call_counts.clear()
