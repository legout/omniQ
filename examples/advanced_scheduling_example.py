"""
Advanced Scheduling Example for OmniQ

This example demonstrates the advanced scheduling features including:
- Cron-like scheduling
- Recurring task management
- Schedule persistence and recovery
- Pause/resume/cancel operations
"""

import asyncio
import time
from datetime import datetime, timedelta
from omniq import OmniQ, ScheduleType, ScheduleStatus


def sample_task(message: str, count: int = 1):
    """Sample task function for scheduling."""
    print(f"[{datetime.now()}] Task executed: {message} (count: {count})")
    return f"Completed: {message}"


def cleanup_task():
    """Sample cleanup task."""
    print(f"[{datetime.now()}] Cleanup task executed")
    return "Cleanup completed"


async def main():
    """Main example function."""
    # Initialize OmniQ
    omniq = OmniQ()
    
    async with omniq:
        # Register functions for scheduling
        omniq.register_function("sample_task", sample_task)
        omniq.register_function("cleanup_task", cleanup_task)
        
        print("=== OmniQ Advanced Scheduling Example ===\n")
        
        # 1. Create a CRON schedule (every minute)
        print("1. Creating CRON schedule (every minute)...")
        cron_schedule_id = await omniq.create_schedule(
            func="sample_task",
            schedule_type=ScheduleType.CRON,
            args=("CRON task",),
            kwargs={"count": 1},
            cron_expression="* * * * *",  # Every minute
            max_runs=3,  # Limit to 3 runs
            metadata={"type": "cron_example"}
        )
        print(f"Created CRON schedule: {cron_schedule_id}")
        
        # 2. Create an INTERVAL schedule (every 30 seconds)
        print("\n2. Creating INTERVAL schedule (every 30 seconds)...")
        interval_schedule_id = await omniq.create_schedule(
            func="sample_task",
            schedule_type=ScheduleType.INTERVAL,
            args=("INTERVAL task",),
            kwargs={"count": 2},
            interval=timedelta(seconds=30),
            max_runs=5,
            metadata={"type": "interval_example"}
        )
        print(f"Created INTERVAL schedule: {interval_schedule_id}")
        
        # 3. Create a TIMESTAMP schedule (run once in 10 seconds)
        print("\n3. Creating TIMESTAMP schedule (run in 10 seconds)...")
        run_time = datetime.utcnow() + timedelta(seconds=10)
        timestamp_schedule_id = await omniq.create_schedule(
            func="cleanup_task",
            schedule_type=ScheduleType.TIMESTAMP,
            timestamp=run_time,
            metadata={"type": "timestamp_example"}
        )
        print(f"Created TIMESTAMP schedule: {timestamp_schedule_id}")
        
        # 4. Start the scheduler
        print("\n4. Starting scheduler...")
        await omniq.start_scheduler()
        print("Scheduler started!")
        
        # 5. List all schedules
        print("\n5. Listing all schedules...")
        schedules = await omniq.list_schedules()
        for schedule in schedules:
            print(f"  - {schedule.id}: {schedule.schedule_type.value} "
                  f"(status: {schedule.status.value}, runs: {schedule.run_count})")
        
        # 6. Let it run for a bit
        print("\n6. Running for 45 seconds...")
        await asyncio.sleep(45)
        
        # 7. Pause the interval schedule
        print("\n7. Pausing interval schedule...")
        paused = await omniq.pause_schedule(interval_schedule_id)
        print(f"Interval schedule paused: {paused}")
        
        # 8. Check schedule status
        interval_schedule = await omniq.get_schedule(interval_schedule_id)
        if interval_schedule:
            print(f"Interval schedule status: {interval_schedule.status.value}")
        
        # 9. Let it run a bit more
        print("\n9. Running for 30 more seconds...")
        await asyncio.sleep(30)
        
        # 10. Resume the interval schedule
        print("\n10. Resuming interval schedule...")
        resumed = await omniq.resume_schedule(interval_schedule_id)
        print(f"Interval schedule resumed: {resumed}")
        
        # 11. Let it run a bit more
        print("\n11. Running for 30 more seconds...")
        await asyncio.sleep(30)
        
        # 12. Cancel the cron schedule
        print("\n12. Cancelling CRON schedule...")
        cancelled = await omniq.cancel_schedule(cron_schedule_id)
        print(f"CRON schedule cancelled: {cancelled}")
        
        # 13. Final schedule status
        print("\n13. Final schedule status...")
        final_schedules = await omniq.list_schedules()
        for schedule in final_schedules:
            print(f"  - {schedule.id}: {schedule.schedule_type.value} "
                  f"(status: {schedule.status.value}, runs: {schedule.run_count})")
        
        # 14. Test schedule recovery
        print("\n14. Testing schedule recovery...")
        recovered_count = await omniq.recover_schedules()
        print(f"Recovered {recovered_count} schedules")
        
        # 15. Stop the scheduler
        print("\n15. Stopping scheduler...")
        await omniq.stop_scheduler()
        print("Scheduler stopped!")
        
        # 16. Clean up - delete schedules
        print("\n16. Cleaning up schedules...")
        for schedule in final_schedules:
            if schedule.status != ScheduleStatus.COMPLETED:
                deleted = await omniq.delete_schedule(schedule.id)
                print(f"Deleted schedule {schedule.id}: {deleted}")


def sync_example():
    """Synchronous example using the sync API."""
    print("\n=== Synchronous API Example ===")
    
    # Initialize OmniQ
    omniq = OmniQ()
    
    with omniq.connection_sync():
        # Register function
        omniq.register_function("sample_task", sample_task)
        
        # Create a simple interval schedule
        schedule_id = omniq.create_schedule_sync(
            func="sample_task",
            schedule_type=ScheduleType.INTERVAL,
            args=("Sync task",),
            interval=timedelta(seconds=5),
            max_runs=3
        )
        print(f"Created sync schedule: {schedule_id}")
        
        # Start scheduler
        omniq.start_scheduler_sync()
        print("Sync scheduler started!")
        
        # Let it run
        time.sleep(20)
        
        # Stop scheduler
        omniq.stop_scheduler_sync()
        print("Sync scheduler stopped!")
        
        # Clean up
        omniq.delete_schedule_sync(schedule_id)
        print("Schedule deleted!")


if __name__ == "__main__":
    # Run async example
    asyncio.run(main())
    
    # Run sync example
    sync_example()
    
    print("\n=== Advanced Scheduling Example Complete ===")