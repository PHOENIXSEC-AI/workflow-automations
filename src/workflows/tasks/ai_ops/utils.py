"""
Utility functions for AI operations.

This module contains helper functions for the AI operations workflow.
"""

import re
import time
import demjson3

from typing import Optional, Dict, Any, List

from prefect import runtime

from pydantic import BaseModel
from pydantic_ai.agent import AgentRunResult

from workflows.agents.models import AgentTask, AgentAnalysisResult
#TODO-Refactor this out 
# from core.services.database.workflow_db_service import WorkflowDatabaseService
from core.utils import LoggerFactory
from core.models import RepomixResultData

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
        logger.warning(msg="Failed to retrieve task_id")
        
    return task_id

def get_runtime_context():
    return {
        "flow_id": runtime.flow_run.id,
        "flow_name": runtime.flow_run.flow_name,
        "flow_run_name": runtime.flow_run.name,
        "flow_run_count": runtime.flow_run.run_count,
        "task_run_id": get_runtime_task_id(),
        "task_run_name": runtime.task_run.name
    }

def get_run_duration(start_time: float) -> float:
    """
    Calculate the duration of a process.
    
    Args:
        start_time: Timestamp when the process started
        
    Returns:
        Duration in seconds as a float
    """
    end_time = time.time()
    return end_time - start_time

def create_agent_tasks(instructions: str, repo_context: RepomixResultData, result_type_schema: BaseModel) -> List[AgentTask]:
    """
    Create a list of agent tasks from repository context with content retrieval.
    
    This function extracts file content from various storage methods and formats
    it into AgentTask objects suitable for AI processing.
    
    Args:
        instructions: A string template with placeholders ({content}, {file_path}, {json_schema})
        repo_context: Dictionary containing repository information including a 'files' list
        result_type: Pydantic model to use for result schema validation
        
    Returns:
        List of AgentTask containing necessary information with retrieved content
    """
    tasks: List[AgentTask] = []
    
    # Track statistics for better logging
    stats = {
        "files_processed": 0,
        "files_skipped": 0, 
        "files_with_separate_storage": 0
    }
    
    for file in getattr(repo_context,'files', []):
        # Process each file in the repository
        stats["files_processed"] += 1
        
        # Extract file path (required)
        file_path = getattr(file,'path','')
        if not file_path:
            logger.warning("Skipping file with missing path")
            stats["files_skipped"] += 1
            continue
        
        try:
            # Get content using helper function
            file_content = getattr(file,'content','')
            # Skip if content retrieval failed
            if not file_content:
                stats["files_skipped"] += 1
                continue
            
            # Format the task with file context
            task_context = instructions.format(
                json_schema=result_type_schema, 
                content=file_content,
                file_path=file_path)
            
            # Create the task
            task = AgentTask(
                instructions=task_context,
                file_path=file_path
            )
            
            # Store task
            tasks.append(task)
            logger.debug(f"Created agent task for file {file_path}")
            
        except Exception as file_error:
            logger.error(f"Error processing file {file_path}: {str(file_error)}")
            stats["files_skipped"] += 1
            continue
                
        
    # # Log detailed statistics
    logger.info(
        f"Created {len(tasks)} agent tasks from repository context. " + 
        f"Files processed: {stats['files_processed']}, " + 
        f"Files skipped: {stats['files_skipped']}, "
    )
    return tasks

def parse_agent_response(task_result: AgentRunResult) -> AgentAnalysisResult:
    """
    Parse the result returned by an AI agent and convert it to a structured AgentAnalysisResult.
    
    Args:
        task_result: Pydantic AI agent model of type AgentRunResult returned by the agent run
        
    Returns:
        AgentAnalysisResult model containing the parsed result data
    """
    # Handle Failed state
    if not task_result.data:
        task_msg = getattr(task_result,'message','')
        err_msg = f"❌ Agent execution failed: {task_msg}"
        logger.error(err_msg)
        return AgentAnalysisResult.create_error_result(err_msg, f"Agent execution failed: {task_msg}")
    
    try:
        # Parse the data if it's a string
        decoded_data = {}
        result_data = getattr(task_result,'data')
        
        if result_data and isinstance(result_data, str):
            try:
                decoded_data = demjson3.decode(result_data)
            except Exception as e:
                return AgentAnalysisResult.create_error_result(
                    f"Failed to parse JSON from agent response", 
                    f"Response is not valid JSON: {result_data[:100]}... Error: {str(e)}"
                )
        elif isinstance(result_data, dict):
            decoded_data = result_data
        else:
            return AgentAnalysisResult.create_error_result(
                f"Unexpected data type from agent", 
                f"Expected string or dict, got {type(result_data).__name__}"
            )
        
        return AgentAnalysisResult.model_validate(decoded_data)
        
    except Exception as e:
        err_msg = f"❌ Error processing agent result: {str(e)}"
        logger.error(err_msg)
        return AgentAnalysisResult.create_error_result(err_msg, f"Error processing result: {str(e)}")

def parse_agent_response_from_str(
    response_str: str, 
    file_path: Optional[str] = 'default'
) -> AgentAnalysisResult:
    """
    Parse a raw string response from an AI agent and convert it to a structured AgentAnalysisResult.
    
    Args:
        response_str: Raw string response from the agent (expected to be parsable JSON)
        file_path: Optional file path to include if not present in the response
        
    Returns:
        AgentAnalysisResult model containing the parsed result data
    """
    if not response_str or not isinstance(response_str, str):
        err_msg = f"❌ Invalid response from agent: Empty or non-string response"
        logger.error(err_msg)
        return AgentAnalysisResult.create_error_result(err_msg, "Empty or invalid response",file_path)
    
    try:
        # Attempt to parse the JSON response
        try:
            data = demjson3.decode(response_str)
        except Exception as e:
            # Handle any parsing errors
            return AgentAnalysisResult.create_error_result(
                f"Failed to parse JSON from agent response", 
                f"Response is not valid JSON: {response_str[:100]}... Error: {str(e)}",
                file_path
            )
            
        # Ensure the expected structure exists
        if not isinstance(data, dict):
            return AgentAnalysisResult.create_error_result(
                "Invalid response format", 
                f"Expected JSON object, got {type(data).__name__}",
                file_path
            )
            
        # Build pydantic model from json
        return AgentAnalysisResult.model_validate(data)
        
    except Exception as e:
        err_msg = f"❌ Error processing agent response: {str(e)}"
        logger.error(err_msg)
        return AgentAnalysisResult.create_error_result(err_msg, f"Error processing response: {str(e)}")

def sanitize_and_parse_agent_response(task_result: Any) -> AgentAnalysisResult:
    """
    Sanitizes the agent response by removing markdown code block formatting artifacts,
    then parses the cleaned response.
    
    Args:
        task_result: The raw result from the agent task
        
    Returns:
        AgentAnalysisResult: The parsed result
    """
    if task_result is None:
        return AgentAnalysisResult.create_error_result("Empty response from agent", "No content to parse")
    
    # Handle string responses
    if isinstance(task_result, str):
        content = task_result
    else:
        return AgentAnalysisResult.create_error_result("Got non string value to parse", "Can't parse non string values")
    
    # Remove markdown code block artifacts
    # Pattern: ```json\n<content>```
    sanitized_content = sanitize_markdown_code_blocks(content)
    
    # Parse the cleaned response
    return parse_agent_response_from_str(sanitized_content)

def sanitize_markdown_code_blocks(content: str) -> str:
    """
    Removes markdown code block formatting artifacts from the content.
    
    Args:
        content: The raw content string
        
    Returns:
        str: The sanitized content
    """
    # Remove opening code block markers like ```json, ```python, etc.
    content = re.sub(r'```[\w]*\n', '', content)
    
    # Remove closing code block markers
    content = re.sub(r'```\s*$', '', content)
    
    # Trim any leading/trailing whitespace
    return content.strip()

__all__ = [
    "parse_agent_response",
    "parse_agent_response_from_str",
    "sanitize_and_parse_agent_response",
    "create_agent_tasks", 
    "get_run_duration", 
    "get_runtime_task_id", 
    "get_runtime_context"]