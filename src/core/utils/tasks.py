import time
from typing import List,Any

from prefect.context import get_run_context

def create_task_batches(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split a list into batches of specified size"""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

# Helper functions for the task
def get_current_retry_count() -> int:
    """Get the current retry count from Prefect context"""
    try:
        context = get_run_context()
        return context.task_run.run_count - 1
    except Exception:
        return 0

def get_current_task_run_id() -> str:
    """Get the current task run ID from Prefect context"""
    try:
        context = get_run_context()
        return str(context.task_run.id)
    except Exception:
        return f"unknown-{time.time()}"

__all__ = ["get_current_task_run_id", "get_current_retry_count", "create_task_batches"]