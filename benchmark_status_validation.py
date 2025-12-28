#!/usr/bin/env python3
"""
Benchmark script for current status validation performance.
This will establish a baseline before optimization.
"""

import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from omniq.models import TaskStatus, can_transition, transition_status
from omniq.models import create_task


def benchmark_current_validation():
    """Benchmark current validation performance."""
    print("=== Current Status Validation Benchmark ===")
    
    # Test transitions for all status combinations
    all_statuses = list(TaskStatus)
    transitions_to_test = []
    
    # Generate all possible transitions
    for from_status in all_statuses:
        for to_status in all_statuses:
            transitions_to_test.append((from_status, to_status))
    
    print(f"Testing {len(transitions_to_test)} status transitions...")
    
    # Benchmark can_transition function
    start_time = time.perf_counter()
    iterations = 100000
    
    for _ in range(iterations):
        for from_status, to_status in transitions_to_test:
            can_transition(from_status, to_status)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    total_checks = iterations * len(transitions_to_test)
    avg_time_per_check = (duration / total_checks) * 1000000  # microseconds
    
    print(f"Current can_transition() performance:")
    print(f"  Total checks: {total_checks:,}")
    print(f"  Total time: {duration:.4f}s")
    print(f"  Avg time per check: {avg_time_per_check:.2f}μs")
    print(f"  Checks per second: {total_checks/duration:,.0f}")
    
    # Test transition_status function (more complex)
    test_task = create_task("test.function", args=[], kwargs={})
    
    start_time = time.perf_counter()
    iterations = 10000
    
    for _ in range(iterations):
        try:
            transition_status(test_task, TaskStatus.RUNNING)
        except ValueError:
            pass  # Expected for some transitions
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"\nCurrent transition_status() performance:")
    print(f"  Total calls: {iterations:,}")
    print(f"  Total time: {duration:.4f}s")
    print(f"  Avg time per call: {(duration/iterations)*1000:.2f}ms")
    
    return avg_time_per_check


def analyze_current_complexity():
    """Analyze current validation code complexity."""
    print("\n=== Current Validation Complexity Analysis ===")
    
    # Count lines in validation functions
    import inspect
    
    # Get source code for key functions
    can_transition_source = inspect.getsource(can_transition)
    transition_status_source = inspect.getsource(transition_status)
    
    can_transition_lines = len([line for line in can_transition_source.split('\n') 
                               if line.strip() and not line.strip().startswith('#')])
    transition_status_lines = len([line for line in transition_status_source.split('\n') 
                                  if line.strip() and not line.strip().startswith('#')])
    
    print(f"Current validation complexity:")
    print(f"  can_transition(): {can_transition_lines} lines")
    print(f"  transition_status(): {transition_status_lines} lines")
    print(f"  Total validation: {can_transition_lines + transition_status_lines} lines")
    
    # Count status values and transitions
    all_statuses = list(TaskStatus)
    print(f"\nCurrent state machine:")
    print(f"  Status values: {len(all_statuses)} ({', '.join(s.value for s in all_statuses)})")
    
    # Count valid transitions
    valid_transition_count = 0
    for from_status in all_statuses:
        for to_status in all_statuses:
            if can_transition(from_status, to_status):
                valid_transition_count += 1
    
    total_possible = len(all_statuses) ** 2
    print(f"  Valid transitions: {valid_transition_count}/{total_possible} ({valid_transition_count/total_possible*100:.1f}%)")


if __name__ == "__main__":
    avg_time = benchmark_current_validation()
    analyze_current_complexity()
    
    print(f"\n=== Baseline Summary ===")
    print(f"Current validation performance: {avg_time:.2f}μs per check")
    print(f"Target after optimization: {avg_time * 0.6:.2f}μs (40% improvement)")
