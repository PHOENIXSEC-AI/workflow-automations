"""
AI Operation Tasks for the workflow system.

This module contains task definitions for AI operations,
including context retrieval and agent execution.
"""

import time
import asyncio
from typing import Union

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from openai import APIConnectionError, APITimeoutError, RateLimitError, APIError

from prefect import task
from prefect.artifacts import create_markdown_artifact
from prefect.states import Failed, Completed
from prefect.cache_policies import NO_CACHE

from core.utils import create_llm_request_error, generic_results_to_markdown, LoggerFactory

from workflows.agents.models import (
    RunAIDeps, 
    RunAITask
)
from workflows.tasks.ai_ops.agent_config import (
    get_async_openrouter_agent, 
    get_async_litellm_proxy_agent 
)
from workflows.tasks.ai_ops.utils import (
    get_run_duration,
    get_runtime_context, 
    parse_agent_response
)

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

# @task(name='get_file_context')
async def get_file_context(db_name: str, coll_name: str, obj_id: str) ->  Union[Completed, Failed]:
    pass
#     """
#     Retrieve a specific file/code document by its ID from MongoDB.
#     If files are chunked, retrieves the full content from GridFS.
    
#     Args:
#         db_name: Name of the MongoDB database
#         coll_name: Name of the MongoDB collection
#         obj_id: Unique identifier for the document to retrieve
        
#     Returns:
#         Prefect state containing the retrieved document or failure information
#     """
#     try:
#         # Retrieve the document by ID
#         search_result = await db_retrieve_document_by_id(
#             doc_id=obj_id, 
#             coll_name=coll_name, 
#             db_name=db_name
#         )
        
#         if search_result.is_failed():
#             err_msg = f"No document found with ID '{obj_id}' in collection '{coll_name}'"
#             logger.error(err_msg)
#             return Failed(message=err_msg)
        
#         search_result = await search_result.result()
        
#         if hasattr(search_result, 'db_result') and search_result.db_result:
#             result_doc = search_result.db_result
            
#             # Log summary of what we received to help diagnose issues
#             repo_name = result_doc.get('repository_name', result_doc.get('repository_url', 'unknown'))
#             summary = result_doc.get('summary', {})
#             total_files = summary.get('total_files', 0) if isinstance(summary, dict) else 0
#             files = result_doc.get('files', [])
            
#             logger.info(f"Retrieved document for '{repo_name}', summary shows {total_files} files, found {len(files)} file entries")
            
#             # Check if document has an error field, indicating a previous issue
#             if 'error' in result_doc:
#                 error_msg = result_doc.get('error', 'Unknown error in document')
#                 logger.error(f"Document contains error: {error_msg}")
#                 # Continue processing anyway - we might still be able to get some files
            
#             # Check if we have files and if they're potentially chunked
#             if len(files) == 0:
#                 logger.warning(f"Document found with ID '{obj_id}', but it has an empty files array")
                
#                 # Check if there are content_ids that indicate chunked files
#                 content_ids = result_doc.get('content_ids', [])
#                 if content_ids:
#                     logger.info(f"Found {len(content_ids)} content_ids, attempting to retrieve chunked files")
#                     # Initialize MongoDB connector to access GridFS
#                     from core.services.database.workflow_db_service import WorkflowDatabaseService
#                     db_service = WorkflowDatabaseService(database=db_name)
                    
#                     # Reconstruct files array with content from GridFS
#                     reconstructed_files = []
#                     for content_id in content_ids:
#                         try:
#                             # Validate content_id
#                             if not content_id:
#                                 logger.error(f"Invalid empty content_id in document {obj_id}")
#                                 continue
                                
#                             # Retrieve file metadata
#                             metadata = result_doc.get('file_metadata', {}).get(content_id, {})
#                             if not isinstance(metadata, dict):
#                                 logger.error(f"Invalid metadata for content_id {content_id}: {metadata}")
#                                 continue
                                
#                             file_path = metadata.get('path', f"file_{content_id}")
                            
#                             # Retrieve content using content_id
#                             content = db_service.retrieve_file_with_tokens(content_id)
                            
#                             # Verify content was successfully retrieved (not an error message)
#                             if isinstance(content, str) and content.startswith("Error:"):
#                                 logger.error(f"Failed to retrieve content for {file_path}: {content}")
#                                 continue
                            
#                             # Add to files array
#                             reconstructed_files.append({
#                                 'path': file_path,
#                                 'content': content,
#                                 'content_id': content_id,
#                                 'metadata': metadata
#                             })
#                             logger.info(f"Retrieved chunked file: {file_path}")
#                         except Exception as e:
#                             logger.error(f"Error retrieving chunked file with content_id {content_id}: {str(e)}")
                    
#                     # Update files array with reconstructed files
#                     files = reconstructed_files
#                     logger.info(f"Reconstructed {len(files)} files from content_ids")
#                 else:
#                     # Check if we have file_ids array, which is another way files might be stored
#                     file_ids = result_doc.get('file_ids', [])
#                     if file_ids:
#                         logger.info(f"Found {len(file_ids)} file_ids, attempting to retrieve files")
#                         from core.services.database.workflow_db_service import WorkflowDatabaseService
#                         db_service = WorkflowDatabaseService(database=db_name)
#                         connector = db_service.connector
                        
#                         reconstructed_files = []
#                         for file_id in file_ids:
#                             try:
#                                 # Retrieve file from GridFS directly
#                                 file_content = connector.retrieve_file_from_gridfs(file_id)
#                                 file_metadata = connector.get_gridfs_metadata(file_id)
                                
#                                 if file_content and file_metadata:
#                                     file_path = file_metadata.get('filename', f"file_{file_id}")
#                                     reconstructed_files.append({
#                                         'path': file_path,
#                                         'content': file_content,
#                                         'file_id': file_id,
#                                         'metadata': file_metadata
#                                     })
#                                     logger.info(f"Retrieved file from GridFS: {file_path}")
#                             except Exception as e:
#                                 logger.error(f"Error retrieving file with file_id {file_id}: {str(e)}")
                        
#                         # Update files array with reconstructed files
#                         files = reconstructed_files
#                         logger.info(f"Reconstructed {len(files)} files from file_ids")
            
#             # Process each file to ensure it has content
#             processed_files = []
#             for file in files:
#                 # Skip non-dict objects or empty dicts
#                 if not isinstance(file, dict) or not file:
#                     logger.warning(f"Skipping invalid file entry: {file}")
#                     continue
                
#                 # Get file path for logging
#                 file_path = file.get('path', 'unknown')
                
#                 # Check if this file has content directly or needs to be retrieved
#                 if not file.get('content') and file.get('content_id'):
#                     try:
#                         # Initialize MongoDB connector if not already done
#                         if 'db_service' not in locals():
#                             from core.services.database.workflow_db_service import WorkflowDatabaseService
#                             db_service = WorkflowDatabaseService(database=db_name)
                        
#                         # Retrieve content using content_id
#                         content_id = file['content_id']
#                         logger.info(f"Retrieving content for file {file_path} using content_id {content_id}")
                        
#                         content = db_service.retrieve_file_with_tokens(content_id)
                        
#                         # Verify content was successfully retrieved (not an error message)
#                         if isinstance(content, str) and content.startswith("Error:"):
#                             logger.error(f"Failed to retrieve content for {file_path}: {content}")
#                             # Include the file anyway, but without content
#                             processed_files.append(file)
#                             continue
                        
#                         # Create a new file dict with the retrieved content
#                         processed_file = file.copy()
#                         processed_file['content'] = content
#                         processed_files.append(processed_file)
#                         logger.info(f"Retrieved content for file {file_path}: {len(content)} bytes")
#                     except Exception as e:
#                         logger.error(f"Error retrieving content for file {file_path}: {str(e)}")
#                         # Include the file anyway, but without content
#                         processed_files.append(file)
#                         continue
                
#                 # Check for GRIDFS reference format
#                 elif isinstance(file.get('content'), str) and file.get('content', '').startswith('GRIDFS:'):
#                     try:
#                         # Initialize MongoDB connector if not already done
#                         if 'db_service' not in locals():
#                             from core.services.database.workflow_db_service import WorkflowDatabaseService
#                             db_service = WorkflowDatabaseService(database=db_name)
                        
#                         gridfs_id = file['content'].split(':', 1)[1]
#                         # Changed to debug level to reduce verbosity
#                         logger.debug(f"Retrieving GridFS content for file {file_path} using ID {gridfs_id}")
                        
#                         content = db_service.connector.retrieve_file_from_gridfs(gridfs_id)
                        
#                         # Create a new file dict with the retrieved content
#                         processed_file = file.copy()
#                         processed_file['content'] = content
#                         processed_files.append(processed_file)
#                         # Changed to debug level to reduce verbosity
#                         logger.debug(f"Retrieved GridFS content for file {file_path}: {len(content)} bytes")
#                     except Exception as e:
#                         logger.error(f"Error retrieving GridFS content for file {file_path}: {str(e)}")
#                         # Include the file anyway, but without content
#                         processed_files.append(file)
#                         continue
#                 else:
#                     # File already has content or doesn't have a content_id
#                     if file.get('content') is not None:
#                         try:
#                             content_len = len(file.get('content', ''))
#                             logger.debug(f"File {file_path} already has content: {content_len} bytes")
#                         except Exception as measure_err:
#                             logger.warning(f"Couldn't measure content length for {file_path}: {str(measure_err)}")
#                     processed_files.append(file)
            
#             # Create the final result object
#             result = {
#                 "coll_name": coll_name,
#                 "obj_id": obj_id,
#                 "repository_name": result_doc.get('repository_url', ''),
#                 "files": processed_files
#             }
            
#             file_count = len(processed_files)
#             success_msg = (
#                 f"✅ Successfully Retrieved Repo Context: '{result['repository_name']}' - "
#                 f"Files Found: {file_count}"
#             )
            
#             if file_count == 0:
#                 logger.warning(f"No files with content found for document '{obj_id}'")
            
#             return Completed(message=success_msg, data=result)
#         else:
#             err_msg = f"❌ Document found, but no content. '{obj_id}' in collection '{coll_name}'"
#             logger.error(err_msg)
#             return Failed(message=err_msg)
            
#     except Exception as e:
#         err_msg = f"❌ Error retrieving document with ID '{obj_id}' from '{db_name}.{coll_name}': {str(e)}"
#         logger.error(err_msg)
#         import traceback
#         logger.error(f"Traceback: {traceback.format_exc()}")
#         return Failed(message=err_msg)

@task(name="run_agent", cache_policy=NO_CACHE)
async def run_agent(ctx: RunAIDeps, instructions: str) -> Union[Completed, Failed]:
    """
    Run an AI agent with the provided context and instructions.
    Results are returned as a structured RunAIResult model.
    
    Args:
        ctx: Context object containing agent configuration
        instructions: Instructions for the agent to process
        
    Returns:
        Prefect state with execution results or failure information, 
        where data is a RunAIResult model instance
    """
    # Validate agent instance
    if not hasattr(ctx, 'shared_agent') or ctx.shared_agent is None:
        return Failed(message="Expected ctx(RunAIDeps) to have shared_agent instance, but got None")
    
    if not hasattr(ctx.shared_agent, 'run'):
        return Failed(message=f"Invalid type for ctx.shared_agent. Expected: Agent, Got: {type(ctx.shared_agent).__name__}")
    
    agent = ctx.shared_agent
    agent_name_to_use = agent.name if hasattr(agent, 'name') and agent.name else "unknown"
    
    # Measure execution time
    agent_start_time = time.time()
    
    logger.info(f"Starting agent: {agent_name_to_use}")
    
    # Define retry decorator for the agent run with enhanced error handling and exponential backoff
    @retry(
        stop=stop_after_attempt(6),  # Increased from 5 to 6
        wait=wait_exponential(multiplier=2, min=2, max=60),  # Increased multiplier and max wait time
        retry=(
            retry_if_exception_type(APIConnectionError) | 
            retry_if_exception_type(APITimeoutError) |
            retry_if_exception_type(RateLimitError) |
            retry_if_exception_type(APIError)
        ),
        reraise=True
    )
    async def run_agent_with_retry(user_instructions):
        try:
            return await agent.run(user_prompt=user_instructions)
        except (APIConnectionError, APITimeoutError) as e:
            # Use our custom error logging function
            context = {"agent": agent_name_to_use, "retry_attempt": True}
            create_llm_request_error(e, context)
            raise  # Re-raise for retry logic
        except RateLimitError as e:
            # Use our custom error logging function
            context = {"agent": agent_name_to_use, "retry_attempt": True, "rate_limited": True}
            create_llm_request_error(e, context)
            raise
        except APIError as e:
            # Use our custom error logging function
            context = {"agent": agent_name_to_use, "retry_attempt": True}
            create_llm_request_error(e, context)
            raise
    
    # Execute agent with instructions using retry logic
    try:
        task_result = await run_agent_with_retry(instructions)
    except RetryError as e:
        # Handle case where all retries were exhausted
        original_error = e.last_attempt.exception()
        context = {
            "agent": agent_name_to_use, 
            "all_retries_exhausted": True,
            "attempts": 6
        }
        create_llm_request_error(original_error, context)
        
        logger.info("Attempting fallback to direct OpenRouter connection...")
        
        try:
            fallback_agent, _ = get_async_openrouter_agent(agent_name_to_use)
            task_result = await fallback_agent.run(user_prompt=instructions)
        except Exception as fallback_error:
            # If fallback also fails, log and return a clear error
            fallback_context = {
                "agent": agent_name_to_use,
                "fallback_attempt": True
            }
            create_llm_request_error(fallback_error, fallback_context)
            err_msg = f"Both LiteLLM proxy and fallback failed: {str(fallback_error)}"
            return Failed(message=err_msg)
    except Exception as e:
        # If unexpected exception occurs outside of retry logic
        context = {"agent": agent_name_to_use, "unexpected_error": True}
        create_llm_request_error(e, context)
        err_msg = f"Unexpected error with LiteLLM proxy: {str(e)}"
        return Failed(message=err_msg)
    
    # Get task context information
    input_ctx = ctx.to_dict()
    runtime_ctx = get_runtime_context()
    
    # Create a properly structured RunAITask object
    task_ctx = RunAITask(
        db_name=input_ctx.get('db_name', ''),
        db_col_name=input_ctx.get('db_col_name', ''),
        target_obj_id=input_ctx.get('target_obj_id', ''),
        flow_id=runtime_ctx.get('flow_id', ''),
        flow_name=runtime_ctx.get('flow_name', ''),
        flow_run_name=runtime_ctx.get('flow_run_name', ''),
        flow_run_count=runtime_ctx.get('flow_run_count', 0),
        task_run_id=runtime_ctx.get('task_run_id', ''),
        task_run_name=runtime_ctx.get('task_run_name', '')
    )
    
    agent_task_duration = get_run_duration(agent_start_time)
    logger.info(f"Agent: {agent_name_to_use} finished. Took: {agent_task_duration:.2f} seconds")
    
    # Parse the agent result with our structured format
    result_data = await parse_agent_response(task_result, agent_name_to_use)
    
    # Create a properly structured RunAIResult
    structured_result = {
        "task": task_ctx.model_dump(),
        "result": result_data.model_dump(),
        "artifact_id": None
    }
    try:
        # Create artifact with result summary
        result_markdown = generic_results_to_markdown(structured_result)
        artifact_id = await create_markdown_artifact(
            markdown=result_markdown, 
            key=f"run-agent-{agent_name_to_use}",
            description=f"Response results from AI Agent"
        )
        structured_result['artifact_id'] = artifact_id if artifact_id else None
        task_msg = f"✅ Run Agent: {agent_name_to_use} completed successfully"
        
    except Exception as e:
        task_msg = f"❌ Agent: {agent_name_to_use} failed to create artifact: {str(e)}"
        logger.error(task_msg)
        # Artifacts are not essential, so if failed we continue
    
    return Completed(message=task_msg, data=structured_result)

@task(name="run_agent_sync", cache_policy=NO_CACHE)
async def run_agent_sync(instructions: str, agent_name: str) -> Union[Completed, Failed]:
    """
    Create and run a new agent instance with the provided instructions.
    Results are returned as a structured RunAIResult model.
    
    Args:
        instructions: Instructions for the agent to process
        agent_name: Name of the agent to create
        
    Returns:
        Prefect state with execution results or failure information,
        where data is a RunAIResult model instance
    """
    # agent, task_specific_agent_name = get_openrouter_agent(agent_name)
    agent, task_specific_agent_name = get_async_litellm_proxy_agent(agent_name)
    if not agent:
        err_msg = f"Agent with name:{agent_name} does not exist. Make sure agent_name param matches those in agent_mapping"
        return Failed(message=err_msg)
    
    agent_start_time = time.time()
    
    logger.info(f"Starting agent: {task_specific_agent_name}")
    
    # Define retry decorator for the agent run with enhanced error handling and exponential backoff
    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=(
            retry_if_exception_type(APIConnectionError) | 
            retry_if_exception_type(APITimeoutError) |
            retry_if_exception_type(RateLimitError) |
            retry_if_exception_type(APIError)
        ),
        reraise=True
    )
    async def run_agent_with_retry(user_instructions):
        try:
            return await agent.run(user_prompt=user_instructions)
        except (APIConnectionError, APITimeoutError) as e:
            # Use our custom error logging function
            context = {"agent": task_specific_agent_name, "retry_attempt": True}
            create_llm_request_error(e, context)
            raise
        except RateLimitError as e:
            # Use our custom error logging function
            context = {"agent": task_specific_agent_name, "retry_attempt": True, "rate_limited": True}
            create_llm_request_error(e, context)
            raise
        except APIError as e:
            # Use our custom error logging function
            context = {"agent": task_specific_agent_name, "retry_attempt": True}
            create_llm_request_error(e, context)
            raise
    
    # Execute agent with instructions using retry logic
    try:
        task_result = await run_agent_with_retry(instructions)
    except RetryError as e:
        # Handle case where all retries were exhausted
        original_error = e.last_attempt.exception()
        context = {
            "agent": task_specific_agent_name, 
            "all_retries_exhausted": True,
            "attempts": 6
        }
        error_details = create_llm_request_error(original_error, context)
        
        # Prefect state to return the warning but treat as failure
        error_msg = f"All retries exhausted for LiteLLM proxy: {error_details['error_message']}"
        return Failed(message=error_msg)
    except Exception as e:
        # Handle unexpected exceptions
        context = {"agent": task_specific_agent_name, "unexpected_error": True}
        error_details = create_llm_request_error(e, context)
        err_msg = f"Unexpected error after unsuccessful retries: {error_details['error_message']}"
        return Failed(message=err_msg)
    
    # Get task context information
    runtime_ctx = get_runtime_context()
    
    # Create a properly structured RunAITask object
    task_ctx = RunAITask(
        db_name='',
        db_col_name='',
        target_obj_id='',
        flow_id=runtime_ctx.get('flow_id', ''),
        flow_name=runtime_ctx.get('flow_name', ''),
        flow_run_name=runtime_ctx.get('flow_run_name', ''),
        flow_run_count=runtime_ctx.get('flow_run_count', 0),
        task_run_id=runtime_ctx.get('task_run_id', ''),
        task_run_name=runtime_ctx.get('task_run_name', '')
    )
    
    agent_task_duration = get_run_duration(agent_start_time)
    logger.info(f"Agent: {agent_name} finished. Took: {agent_task_duration:.2f} seconds")
    
    # Parse the agent result with our structured format
    result_data = await parse_agent_response(task_result, agent_name)
    
    # Create a properly structured RunAIResult
    structured_result = {
        "task": task_ctx.model_dump(),
        "result": result_data,
        "artifact_id": None
    }
    try:
        # Create artifact with result summary
        result_markdown = generic_results_to_markdown(structured_result)
        artifact_id = await create_markdown_artifact(
            markdown=result_markdown, 
            key=f"run-agent-{agent_name}",
            description=f"Response results from AI Agent"
        )
        structured_result['artifact_id'] = artifact_id if artifact_id else None
        task_msg = f"✅ Run Agent: {agent_name} completed successfully"
        
    except Exception as e:
        task_msg = f"❌ Agent: {agent_name} failed to create artifact: {str(e)}"
        logger.error(task_msg)
        # Artifacts are not essential, so if failed we continue
    
    return Completed(message=task_msg, data=structured_result)


__all__ = ["run_agent_sync", "run_agent", "get_file_context"] 