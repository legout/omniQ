import asyncio
import inspect
import logging
import time

from omniq.core import OmniQ
from omniq.models import Task, TaskResult
from omniq.serialization import default_serializer
from omniq.models import TaskEvent

logger = logging.getLogger(__name__)


async def execute_task(
    omniq: OmniQ, task: Task, worker_id: str, running_in_thread: bool = False
) -> None:
    """
    A standalone function to deserialize and execute a task, handling results and errors.
    This can be used by any worker type.
    """
    start_time = time.time()
    try:
        # The entire Task object is serialized/deserialized, so fields are ready to use.
        func = task.func
        args = task.args
        kwargs = task.kwargs

        if omniq.event_storage:
            await omniq.event_storage.log(TaskEvent(task_id=task.id, event_type="EXECUTING"))

        logger.info(f"Executing task {task.id} from queue '{task.queue}'")

        # Execute the function
        if inspect.iscoroutinefunction(func):
            result_val = await func(*args, **kwargs)
        elif running_in_thread:
            # Already in a dedicated thread/process, call the sync function directly
            result_val = func(*args, **kwargs)
        else:
            # In an async worker, run sync functions in an executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            result_val = await loop.run_in_executor(None, func, *args, **kwargs)

        result = TaskResult(
            
            task_id=task.id,
            status="SUCCESS",
            result=default_serializer.serialize(result_val),
            started_at=start_time,
            worker_id=worker_id,
        )
        await omniq.result_storage.store(result)
        await omniq.task_queue.ack(task)
        logger.info(f"Task {task.id} completed successfully.")
        if omniq.event_storage:
            await omniq.event_storage.log(TaskEvent(task_id=task.id, event_type="COMPLETED", details={"result": str(result_val)}))

     
    except Exception as e:
        logger.error(f"Task {task.id} failed: {e}", exc_info=True)
        result = TaskResult(
            task_id=task.id,
            status="FAILURE",
            result=default_serializer.serialize(str(e)),
            started_at=start_time,
            worker_id=worker_id,
        )
        await omniq.result_storage.store(result)
        # Basic retry logic
        if task.retries < task.max_retries:
            task.retries += 1
            await omniq.task_queue.nack(task, requeue=True)
            logger.info(f"Task {task.id} failed, retrying ({task.retries}/{task.max_retries}).")
        else:
            await omniq.task_queue.nack(task, requeue=False)
            logger.error(f"Task {task.id} failed after {task.max_retries} retries. Moved to dead-letter queue.")
            if omniq.event_storage:
                await omniq.event_storage.log(TaskEvent(task_id=task.id, event_type="FAILED", details={"error": str(e)}))