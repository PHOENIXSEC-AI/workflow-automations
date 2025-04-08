# Standard library imports
import time
import asyncio
from typing import Any, Dict, List, Optional, Union

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from prefect import flow, task, unmapped
from prefect.cache_policies import NO_CACHE
from prefect.futures import wait
from prefect.states import Completed, Failed
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.tasks import exponential_backoff
from pydantic_ai import Agent

# Local application imports
from core.utils import (
    create_task_batches,
    get_current_retry_count,
    get_current_task_run_id,
    get_flow_name,
    LoggerFactory
)
from workflows.agents.models import (
    AgentBatchResult,
    AgentErrorResult,
    AgentResult,  # Unparsed raw str content returned by LLM
    AgentSuccessResult,
    AgentTask,
    AgentAnalysisResult, # Parsed str content into pydantic model
    RunAIDeps,
    RunAgentDeps,
    TokenUsage
)
from workflows.tasks.ai_ops.agent_config import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_TEMP,
    get_async_openai_agent,
    get_async_pydanticai_agent
)
from workflows.tasks.ai_ops.tasks import get_file_context
from workflows.tasks.ai_ops.utils import create_agent_tasks

from core.config import app_config
from core.models import RepoAnalysisResult

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

"""
Concurrent agent execution flow module.

This module provides functionality for running multiple AI agent tasks concurrently 
with proper batching, retry logic, and result aggregation. It supports both PydanticAI 
and OpenAI-compatible interfaces with comprehensive error handling.
"""

@flow(
    log_prints=True, 
    name="run_concurrent_agents",
    task_runner=ThreadPoolTaskRunner(max_workers=app_config.MAX_WORKERS)
)
async def run_concurrent_agents(
    ctx: RunAgentDeps,
    instructions: str,
    agent_name: str = "env-vars-extractor",
    max_retries: int = 3,
    timeout_seconds: int = 120,
) -> Union[Completed,Failed]:
    """
    Flow that runs concurrent agent tasks using PydanticAI across repository context.
    
    This flow retrieves file contexts from a database, creates agent tasks, and runs them
    in parallel batches with configurable retry logic and timeouts. Results are collected
    and aggregated into a single response.
    
    Args:
        ctx: RunAIDeps object containing database connection details and target object ID
        instructions: Prompt instructions to send to the agent
        agent_name: Name of the agent configuration to use (default: "env-vars-extractor")
        max_retries: Maximum number of retries for each task (default: 3)
        timeout_seconds: Timeout in seconds for each task (default: 120)
        
    Returns:
        Union[Completed,Failed]: Prefect state with AgentBatchResult data on success,
        or Failed state if no results were successful
    """
    assert ctx is not None
    assert ctx.repomix_data is not None
    
    if not hasattr(ctx.result_type,'model_json_schema'):
        err_msg = f"Error: No expected return type configured for `run_concurrent_agents`: {repo_url}"
        logger.error(err_msg)
        return Failed(message=f"FAIL: {err_msg}")  
    
    
    llm_return_data_schema = ctx.result_type.model_json_schema()
    repomix_result_data = getattr(ctx.repomix_data,'result', None)
    files = getattr(repomix_result_data,'files', [])
    
    repo_url = getattr(ctx.repomix_data, 'repository_url', '')
    repo_name = repo_url.split('/')[-1]
    
    logger.info(f"Retrieved repository context for concurrent agents: {repo_url}, {len(files)} files")

    tasks = []
    
    # # Otherwise, create tasks from repository files
    tasks = create_agent_tasks(
        instructions=instructions, 
        repo_context=repomix_result_data, 
        result_type_schema=llm_return_data_schema
    )
    
    # Check if we have tasks to process
    if not tasks:
        err_msg = f"Error: No tasks created for repository {repo_url}"
        logger.error(err_msg)
        return Failed(message=f"FAIL: {err_msg}")
    
    logger.debug(f"Created {len(tasks)} tasks to process")
    
    # Configure agent and task
    task_build_kwargs = {
        "retries":max_retries,
        "retry_delay_seconds":exponential_backoff(backoff_factor=2),
        "timeout_seconds":timeout_seconds,
        "tags":[agent_name, repo_name, "llm", "pydantic-ai"]
    }
    agent, config = get_async_pydanticai_agent(agent_name)
    
    configured_task = run_agent_pydantic.with_options(**task_build_kwargs)
    logger.debug(f"Agent Task Configuration: {task_build_kwargs}")
    
    # Process in batches
    success_results = []
    fail_results = []
    batches = create_task_batches(tasks, app_config.MAX_WORKERS)
    logger.info(f"Processing {len(tasks)} tasks in {len(batches)} batches")
    
    for i, batch in enumerate(batches):
        batch_size = len(batch)
        logger.info(f"Starting batch {i+1}/{len(batches)} with {batch_size} tasks")
        
        # Process batch
        batch_futures = configured_task.map(
            task=batch,
            agent_name=unmapped(agent_name),
            shared_client=unmapped(agent),
            config=unmapped(config)
        )
        
        batch_completed = wait(batch_futures).done
        
        # Split into successful and failed tasks
        success_tasks = [future for future in batch_completed if not future.state.is_failed()]
        failed_tasks = [future for future in batch_completed if future.state.is_failed()]
        
        # Get results from each task
        batch_results_ok = [future.result() for future in success_tasks]
        batch_results_fail = [future.result() for future in failed_tasks]
        
        # Add batch results to overall results
        success_results.extend(batch_results_ok)
        fail_results.extend(batch_results_fail)
        
        # Calculate batch statistics
        batch_success_count = len(success_tasks)
        overall_success_count = len(success_results)
        overall_fail_count = len(fail_results)
        
        # Log detailed batch results
        logger.info(f"Batch {i+1} completed: {batch_success_count}/{batch_size} successful")
        logger.info(f"  - Cumulative progress: {overall_success_count} successful, {overall_fail_count} failed")
    
    # Create a final obj that this task will return
    final_result = AgentBatchResult(
        successful=len(success_results),
        failed=len(fail_results),
        total_tasks=len(tasks)
    )
    
    # Get Agent response message for parsing
    agent_response_content = [(agent_response.task,agent_response.result) for agent_response in success_results]
    
    # Build final result obj
    for task_ctx, agent_response in agent_response_content:
        try:
            # Dumping to ensure all extra fields from agent_response are included
            # Make sure both objects are Pydantic models before using model_dump()
            if hasattr(task_ctx, 'model_dump') and hasattr(agent_response, 'model_dump'):
                response_w_task_ctx = task_ctx.model_dump() | agent_response.model_dump()
            else:
                logger.error(f"Expected Pydantic models, got {type(task_ctx)} and {type(agent_response)}")
                continue
            
            final_result.results.append(response_w_task_ctx)
        except Exception as e:
            logger.error(f"Failed to merge task_ctx and agent_response, type(`agent_response`): {type(agent_response).__name__}: {str(e)}")
            continue
    
    if not final_result.results:
        return Failed(message=f"FAIL: {get_flow_name()}")
    
    logger.info(f"  - Cumulative progress: Total: {final_result.total_tasks} of which: {final_result.successful} successful, {final_result.failed} failed")
    return Completed(data=final_result,message=f"✅ OK: Run Concurrent Agents Completed Successfully")

@task(
    name="run_agent_pydantic",
    retries=3,  # Number of retries
    retry_delay_seconds=exponential_backoff(backoff_factor=2),  # Exponential backoff
    retry_jitter_factor=0.2,  # Add jitter to prevent thundering herd
    tags=["ai", "agent", "llm", "pydantic-ai"],  # Tags for filtering in the UI
    timeout_seconds=120,  # Maximum time the task can run
    persist_result=app_config.is_development(),  # Persist the result for debugging
    cache_key_fn=None,  # Could add caching based on prompt hash for identical requests
    cache_policy=NO_CACHE,
)
async def run_agent_pydantic(
    task: AgentTask,
    agent_name: str,
    user_prompt: Optional[str] = None, 
    shared_client: Optional[Agent] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Union[Completed, Failed]:
    """
    Enhanced run_agent_pydantic task with comprehensive error handling and recovery using PydanticAI.
    
    This task sends a prompt to a PydanticAI agent and handles all error cases with proper
    retry logic and timeout management. It uses a structured approach to return pydantic model
    instances parsed from the agent response.
    
    Args:
        task: Task object containing instructions and metadata
        agent_name: Name of the agent to use
        user_prompt: Optional user prompt to override task.instructions
        shared_client: Optional shared PydanticAI Agent client
        config: Optional configuration parameters
        
    Returns:
        Union[Completed, Failed]: Where the Prefect state's data attribute contains an AgentResult
        (either AgentSuccessResult or AgentErrorResult)
    """
    # Track execution time
    start_time = time.time()
    
    # Initialize tracking context
    context = {
        "agent": agent_name,
        "retry_count": get_current_retry_count(),
        "task_run_id": get_current_task_run_id(),
    }
    
    if not task.instructions:
        raise ValueError(f"instructions are required for `run_agent_pydantic` task. Make sure param task has valid `instruction` field")
    
    # Use provided client or create a new one
    agent = shared_client
    if not agent:
        agent, agent_config = get_async_pydanticai_agent(agent_name)
        config = agent_config
    
    # Determine which prompt to use (user_prompt has priority over task.instructions)
    prompt_to_use = user_prompt or task.instructions
    
    # Create a more configurable timeout with safety margin
    timeout_seconds = config.get("timeout_seconds", 90)  # Default 90 seconds
    # Add a 10% safety margin to prevent task timeout before inner timeout
    inner_timeout = min(timeout_seconds * 0.9, timeout_seconds - 5)
    
    try:
        # Make the API call with timeout guard
        agent_response = await asyncio.wait_for(
            agent.run(
                prompt_to_use
            ),
            timeout=inner_timeout
        )
        
        # Process successful response
        if agent_response and hasattr(agent_response, 'data'):
            result = agent_response.data
            # If result is not a string, convert it to a string representation
            if not isinstance(result, AgentAnalysisResult):
                error_result = AgentErrorResult(
                    task=task,
                    error_type="invalid_response",
                    message=f"Agent Response is not a valid AgentAnalysisResult instance. Got {type(result)}"
                )
                return Failed(data=error_result, message="Agent Response is invalid, either parsing was unsuccessful or did not execute at all")

            duration = time.time() - start_time
            
            
            success_result = AgentSuccessResult(
                task=task,
                result=result,
                duration_seconds=duration,
                agent=agent_name,
                model=config.get("model"),
            )
            return Completed(
                data=success_result, 
                message=f"Agent {agent_name} completed successfully in {duration:.2f}s. Retry attempts: {get_current_retry_count()+1}")
        
        # Handle empty response (unlikely but possible)
        logger.warning(f"Agent {agent_name} returned empty response")
        error_result = AgentErrorResult(
            task=task,
            error_type="empty_response",
            message=f"The LLM returned an empty response for model {config.get('model')}"
        )
        return Failed(data=error_result, message="Agent returned empty response")
    
    except asyncio.TimeoutError as e:
        # Our own timeout guard triggered
        duration = time.time() - start_time
        logger.warning(f"Internal timeout for agent {agent_name} after {duration:.2f}s")
        
        # Raise for Prefect to handle retry
        raise asyncio.TimeoutError(f"Internal timeout after {duration:.2f}s")
        
    except Exception as e:
        # Catch all other exceptions - PydanticAI will have its own error types
        duration = time.time() - start_time
        
        # Determine if this is a retryable error
        error_class = e.__class__.__name__
        retryable_errors = [
            "TimeoutError", 
            "RateLimitError", 
            "APIConnectionError", 
            "ServiceUnavailableError"
        ]
        
        if error_class in retryable_errors:
            logger.warning(f"Expected error: {str(e)} for agent {agent_name} after {duration:.2f}s execution - Will Retry... ")
            # Raise for Prefect to handle retry
            raise e
        logger.error(f"Unexpected error for agent {agent_name} after {duration:.2f}s: {str(e)}")
        error_result = AgentErrorResult(
            task=task,
            error_type="unexpected",
            message=str(e),
            exception_type=error_class
        )
        return Failed(data=error_result, message=f"Agent {agent_name} encountered unexpected error: {str(e)}")


@task(
    name="run_agent_openai",
    retries=3,  # Number of retries
    retry_delay_seconds=exponential_backoff(backoff_factor=2),  # Exponential backoff
    retry_jitter_factor=0.2,  # Add jitter to prevent thundering herd
    tags=["ai", "agent", "llm", "openai"],  # Tags for filtering in the UI
    timeout_seconds=120,  # Maximum time the task can run
    persist_result=app_config.is_development(),  # Persist the result for debugging
    cache_key_fn=None,  # Could add caching based on prompt hash for identical requests
    cache_policy=NO_CACHE,
)
async def run_agent_openai(
    task: AgentTask,
    agent_name: str,
    max_tokens: int = 4000,
    temperature: Optional[float] = DEFAULT_MODEL_TEMP,
    user_prompt: Optional[str] = None, 
    shared_client: Optional[AsyncOpenAI] = None,
    system_prompt: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Union[Completed, Failed]:
    """
    Run an OpenAI-compatible agent task with comprehensive error handling and recovery.
    
    This task sends a prompt to an OpenAI-compatible API and handles all error cases with
    proper retry logic and timeout management. It can communicate with OpenRouter and
    other OpenAI-compatible services.
    
    Args:
        task: Task object containing instructions and metadata
        agent_name: Name of the agent to use
        max_tokens: Maximum tokens to generate in response (default: 4000)
        temperature: Sampling temperature (default: from app_config)
        user_prompt: Optional user prompt to override task.instructions
        shared_client: Optional shared AsyncOpenAI client
        system_prompt: Optional system prompt to override default
        config: Optional configuration parameters
        
    Returns:
        Union[Completed, Failed]: Where the Prefect state's data attribute contains an AgentResult
        (either AgentSuccessResult or AgentErrorResult)
    """
    # Track execution time
    start_time = time.time()
    
    # Initialize tracking context
    context = {
        "agent": agent_name,
        "retry_count": get_current_retry_count(),
        "task_run_id": get_current_task_run_id(),
    }
    
    
    if not task.instructions:
        raise ValueError(f"instructions are required for `run_agent` task. Make sure param task has valid `instruction` field")
    
    # Use provided client or create a new one
    client = shared_client
    if not client:
        client, agent_config = get_async_openai_agent(agent_name)
        config = agent_config
    
    
    # Use provided system prompt or get from config
    system_message = system_prompt or config.get("system_prompt", "")
    if not system_message:
        system_message = "You are helpful assistant"
        logger.warning(f"task `run_agent_openai` created without system_prompt. Make sure agent_config is configured. Using default: `{system_message}`")
    
    # Prepare headers with request ID for tracing
    headers = dict(config.get("headers", {}))
    headers["X-Request-ID"] = f"run-{context['task_run_id']}"
    
    # Create a more configurable timeout with safety margin
    timeout_seconds = config.get("timeout_seconds", app_config.HTTPX_TIMEOUT_SECONDS)
    # Add a 10% safety margin to prevent task timeout before inner timeout
    inner_timeout = min(timeout_seconds * 0.9, timeout_seconds - 5) 
    
    # Determine which prompt to use (user_prompt has priority over task.instructions)
    prompt_to_use = user_prompt or task.instructions
    
    try:
        # Make the API call with timeout guard
        model_to_use = config.get("model", None)
        if not model_to_use:
            model_to_use = DEFAULT_MODEL
            logger.warning(f"Model name not found in agent_config, using default: {model_to_use}")
        
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_to_use}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                extra_headers=headers
            ),
            timeout=inner_timeout
        )
        
        # Process successful response
        if response.choices:
            result = response.choices[0].message.content
            duration = time.time() - start_time
            
            # Create token usage data if available
            token_usage = None
            if hasattr(response, 'usage'):
                token_usage = TokenUsage(
                    prompt=response.usage.prompt_tokens if hasattr(response.usage, "prompt_tokens") else None,
                    completion=response.usage.completion_tokens if hasattr(response.usage, "completion_tokens") else None,
                    total=response.usage.total_tokens if hasattr(response.usage, "total_tokens") else None,
                )
            
            success_result = AgentSuccessResult(
                task=task,
                result=result,
                duration_seconds=duration,
                agent=agent_name,
                model=model_to_use,
                tokens=token_usage
            )
            return Completed(
                data=success_result, 
                message=f"Agent {agent_name} completed successfully in {duration:.2f}s. Retry attempts: {get_current_retry_count()+1}")
        
        # Handle empty response (unlikely but possible)
        logger.warning(f"Agent {agent_name} returned empty response")
        error_result = AgentErrorResult(
            task=task,
            error_type="empty_response",
            message=f"The LLM returned an empty response for model {model_to_use}"
        )
        return Failed(data=error_result, message="Agent returned empty response")
    except APITimeoutError as e:
        # Timeout errors are usually retryable
        duration = time.time() - start_time
        logger.warning(f"Timeout error for agent {agent_name} after {duration:.2f}s: {str(e)}")
        
        # Raise for Prefect to handle retry - don't add a message
        raise e
            
    except APIConnectionError as e:
        # Connection errors are usually retryable
        duration = time.time() - start_time
        logger.warning(f"Connection error for agent {agent_name} after {duration:.2f}s: {str(e)}")
        
        # Raise for Prefect to handle retry - don't add a message
        raise e
        
    except RateLimitError as e:
        # Rate limit errors should retry with increasing backoff
        duration = time.time() - start_time
        logger.warning(f"Rate limit error for agent {agent_name} after {duration:.2f}s: {str(e)}")
        
        # Raise for Prefect to handle retry with exponential backoff - don't add a message
        raise e
        
    except APIError as e:
        # API errors may be retryable depending on status code
        duration = time.time() - start_time
        status_code = getattr(e, "status_code", 0)
        
        # 429, 500, 502, 503, 504 are typically retryable
        retryable_codes = {429, 500, 502, 503, 504}
        if status_code in retryable_codes:
            raise e
        else:
            # Non-retryable API error, return error response
            logger.error(f"Non-retryable API error {status_code} for agent {agent_name}: {str(e)}")
            error_result = AgentErrorResult(
                task=task,
                error_type="api_error",
                status_code=status_code,
                message=str(e)
            )
            return Failed(data=error_result, message=f"Agent {agent_name} encountered API error: {str(e)}")
            
    except asyncio.TimeoutError as e:
        # Our own timeout guard triggered
        duration = time.time() - start_time
        logger.warning(f"Internal timeout for agent {agent_name} after {duration:.2f}s")
        
        # Raise for Prefect to handle retry
        raise asyncio.TimeoutError(f"Internal timeout after {duration:.2f}s")
        
    except Exception as e:
        # Catch all other exceptions
        duration = time.time() - start_time
        logger.error(f"Unexpected error for agent {agent_name} after {duration:.2f}s: {str(e)}")
        
        error_result = AgentErrorResult(
            task=task,
            error_type="unexpected",
            message=str(e),
            exception_type=type(e).__name__
        )
        return Failed(data=error_result, message=f"Agent {agent_name} encountered unexpected error: {str(e)}")


__all__ = ["run_concurrent_agents"]