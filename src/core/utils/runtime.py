"""
Utility functions for runtime context.
"""
from typing import Dict, Any, Optional
from prefect import runtime

from core.utils.logger import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

def get_runtime_task_id() -> str:
    """
    Get the current Prefect task run ID.
    
    Returns:
        A string with the task ID, or empty string if retrieval fails
    """
    task_id = ""
    if hasattr(runtime, 'task_run') and hasattr(runtime.task_run, 'id'):
        if isinstance(runtime.task_run.id, str):
            task_id = runtime.task_run.id
    
    if not task_id:
        logger.warning("Failed to retrieve task_id")
        
    return task_id

def get_ai_run_context() -> Dict[str, Any]:
    """
    Get AI context from runtime parameters.
    
    Returns:
        Dictionary with AI context or empty dict if not available
    """
    if 'ctx' in runtime.task_run.parameters and hasattr(runtime.task_run.parameters['ctx'], 'to_dict'):
        # The object exists and has a to_dict method
        ctx_dict = runtime.task_run.parameters['ctx'].to_dict()
        return ctx_dict

    return {}

def get_runtime_context() -> Dict[str, Any]:
    """
    Get Prefect runtime context information.
    
    Returns:
        Dictionary with flow and task information
    """
    return {
        "flow_id": runtime.flow_run.id,
        "flow_name": runtime.flow_run.flow_name,
        "flow_run_name": runtime.flow_run.name,
        "flow_run_count": runtime.flow_run.run_count,
        "task_run_id": get_runtime_task_id(),
        "task_run_name": runtime.task_run.name
    }

def get_flow_name() -> str:
    return f'{runtime.flow_run.flow_name}:{runtime.flow_run.name}'