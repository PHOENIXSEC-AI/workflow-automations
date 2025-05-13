import os
from typing import Dict, Any, Union
from datetime import datetime, timezone

import warnings
# Filter warnings about propagated trace context that may appear with distributed tracing
warnings.filterwarnings("ignore", message="Found propagated trace context")

from prefect import flow, task
from prefect.states import Completed, Failed
from prefect.artifacts import create_markdown_artifact

from core.utils import get_utc_date, LoggerFactory
from core.utils.format import generic_results_to_markdown
from core.models import RepoAnalysisTask

from workflows.tasks import analyze_local_repo, parse_tool_results, fetch_private_github_repo

from core.config import app_config
# Set up logger with modified settings to reduce verbosity
logger = LoggerFactory.get_logger(
    name=app_config.APP_TITLE,
    log_level=app_config.log_level, 
    trace_enabled=True
)

@task(name="prepare_private_analysis_metadata")
def prepare_private_analysis_metadata(
    task: RepoAnalysisTask, 
    local_repo_path: str
) -> Dict[str, Any]:
    """
    Prepare metadata for the private repository analysis.
    
    Args:
        task: The repository analysis task parameters
        local_repo_path: Path to the locally fetched repository
        
    Returns:
        Dictionary containing metadata about the analysis
    """
    # Extract repository name from URL
    repo_name = task.github_repo_url.split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    return {
        "repository_url": task.github_repo_url,
        "repository_name": repo_name,
        "local_repo_path": local_repo_path,
        "analysis_timestamp": get_utc_date(),
        "config_used": task.repomix_config_path,
        "is_private": True
    }

@flow(
    log_prints=False,  # Changed to False to reduce verbosity
    name="run_private_repo_analysis", 
    description="Fetch a private GitHub repository, analyze it using Repomix, and store the results"
)
def run_private_repo_analysis(task: RepoAnalysisTask) -> Union[Completed,Failed]:
    """
    Flow to analyze a private GitHub repository.
    
    This flow requires the GITHUB_TOKEN environment variable to be set with a valid
    GitHub personal access token (starting with 'ghp_').
    
    Args:
        task: The repository analysis task parameters
        
    Returns:
        Prefect state containing the analysis results
    """
    # Check if GITHUB_TOKEN is set
    if "GITHUB_TOKEN" not in os.environ:
        return Failed(message="GITHUB_TOKEN environment variable is not set. Required for accessing private repositories.")
    
    # Validate inputs
    if not task.github_repo_url:
        return Failed(message="Private GitHub Repository URL is required")
    
    if not task.repomix_config_path:
        return Failed(message="Repomix Config Path is required")
    
    # Determine output path
    default_output_path = "/tmp"  # Use /tmp instead of config path for output
    output_file = f"private-analysis-{datetime.now(tz=timezone.utc).strftime('%Y%m%d-%H%M%S')}.xml"
    
    output_path = os.path.join(task.output_path or default_output_path, output_file)
    
    logger.debug(f"Setting output path to: {output_path}")
    
    try:
        # Step 1: Fetch the private GitHub repository
        logger.info(f"Fetching repository: {task.github_repo_url}")
        fetch_result = fetch_private_github_repo(task.github_repo_url)
        
        if fetch_result.is_failed():
            error_msg = f"Failed to fetch private repository: {fetch_result.message}"
            logger.error(error_msg)
            return Failed(data={"error": error_msg}, message=error_msg)
        
        # Extract local repository path
        fetch_data = fetch_result.result()
        local_repo_path = fetch_data.get('result_dir')
        if not local_repo_path or not os.path.exists(local_repo_path):
            error_msg = f"Invalid local repository path: {local_repo_path}"
            logger.error(error_msg)
            return Failed(data={"error": error_msg}, message=error_msg)
        
        logger.info(f"Repository fetched to: {local_repo_path}")
        
        # Prepare metadata
        metadata = prepare_private_analysis_metadata(task, local_repo_path)
        
        # Step 2: Run repository analysis on the local repository
        logger.info(f"Analyzing local repository: {local_repo_path}")
        analysis_result = analyze_local_repo(
            local_repo_path, 
            task.repomix_config_path,
            output_path
        )
        
        if analysis_result.is_failed():
            error_msg = f"Repository analysis failed: {analysis_result.message}"
            logger.error(error_msg)
            return Failed(data={"error": error_msg}, message=error_msg)
        
        # Extract result data
        analysis_data = analysis_result.result()
        result_file_path = analysis_data['output_path'] if 'output_path' in analysis_data else None
        
        # Step 3: Parse tool results
        logger.info(f"Parsing analysis results")
        if app_config.is_development():
            logger.debug(f"Parsing from: {result_file_path}")
            
        parse_result = parse_tool_results(result_path=result_file_path)
        
        if parse_result.is_failed():
            error_msg = f"Failed to parse analysis results: {parse_result.message}"
            logger.error(error_msg)
            return Failed(
                data={"error": error_msg, "analysis_data": analysis_data}, 
                message=error_msg
            )
        
        # Extract parsed results
        parsed_data = parse_result.data
        if not parsed_data:
            error_msg = "Parse tool returned empty results"
            logger.error(error_msg)
            return Failed(
                data={"error": error_msg, "analysis_data": analysis_data},
                message=error_msg
            )
        
        final_result = parse_result.result()
        
        if hasattr(final_result, 'model_dump'):
            final_result = final_result.model_dump()
        elif isinstance(final_result, dict):
            final_result = final_result
        else:
            error_msg = f"Expected dict or Pydantic model, got {type(final_result)}"
            logger.error(error_msg)
            return Failed(
                data={"error": error_msg, "analysis_data": analysis_data, "parsed_data":final_result},
                message=error_msg
            )
        
        # Add metadata to results
        final_result.update(metadata)
        
        # Create a summary markdown artifact
        summary = {
            "repository": task.github_repo_url,
            "local_path": local_repo_path,
            "analysis_completed": True,
            "errors": final_result.get('errors', [])
        }
        
        summary_markdown = generic_results_to_markdown(summary)
        create_markdown_artifact(
            markdown=summary_markdown,
            key="private-repo-analysis-summary",
            description=f"Private Repository Analysis Summary for {task.github_repo_url}"
        )
        
        return Completed(data=final_result, message="✅ Private repository analysis completed successfully")
        
        
    except Exception as e:
        error_msg = f"Private repository analysis flow failed: {str(e)}"
        logger.error(error_msg)
        return Failed(data={"error": str(e)}, message=error_msg)

__all__ = ["run_private_repo_analysis"]