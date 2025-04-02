import os
from typing import Dict, Any, Optional
from datetime import datetime

from prefect import flow, task
from prefect.input import RunInput
from prefect.states import Completed, Failed
from prefect.artifacts import create_markdown_artifact

from core.utils import LoggerFactory, get_utc_date
from core.utils.format import generic_results_to_markdown
from workflows.tasks import analyze_remote_repo, parse_tool_results, store_results

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

class RepoAnalysisTask(RunInput):
    """
    Input parameters for the repository analysis flow.
    
    Attributes:
        remote_repo_url: URL of the remote Git repository to analyze
        repomix_config_path: Path to the Repomix configuration file
        output_path: Optional custom path for analysis output
        debug: Enable debug mode for additional logging
    """
    github_repo_url: str
    repomix_config_path: str
    output_path: Optional[str] = None
    debug: bool = False

@task(name="prepare_analysis_metadata")
def prepare_analysis_metadata(task: RepoAnalysisTask) -> Dict[str, Any]:
    """
    Prepare metadata for the repository analysis.
    
    Args:
        task: The repository analysis task parameters
        
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
        "analysis_timestamp": get_utc_date(),
        "config_used": task.repomix_config_path,
        "debug_mode": task.debug
    }

@flow(
    log_prints=True, 
    name="run_repo_analysis", 
    result_storage="local-file-system/dev-result-storage",
    description="Analyze a Git repository using Repomix and store the results"
)
def run_repo_analysis(task: RepoAnalysisTask):
    """
    Flow to analyze a remote Git repository.
    
    Args:
        task: The repository analysis task parameters
        
    Returns:
        Prefect state containing the analysis results
    """
    # Validate inputs
    if not task.github_repo_url:
        return Failed(message="Remote Github Repository URL is required")
    
    if not task.repomix_config_path:
        return Failed(message="Repomix Config Path is required")
    
    # Determine output path
    default_output_path = '/workspaces/workflow-automation/src/tools/repomix/reports'
    output_file = f"analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xml"
    
    output_path = os.path.join(task.output_path or default_output_path, output_file)
    
    # Prepare metadata
    metadata = prepare_analysis_metadata(task)
    
    try:
        # Step 1: Run repository analysis
        logger.info(f"Starting analysis of repository: {task.github_repo_url}")
        analysis_result = analyze_remote_repo(
            task.github_repo_url, 
            task.repomix_config_path,
            output_path
        )
        
        if analysis_result.is_failed():
            error_msg = f"Repository analysis failed: {analysis_result.message}"
            logger.error(error_msg)
            return Failed(data={"error": error_msg}, message=error_msg)
        
        # Extract result data
        # analysis_data = analysis_result.data.result
        analysis_data = analysis_result.result()
        result_file_path = analysis_data['output_path'] if 'output_path' in analysis_data else None
        
        # Step 2: Parse tool results
        logger.info(f"Parsing analysis results from: {result_file_path}")
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
        
        # Step 3: Store results
        logger.info("Storing analysis results in database")
        store_result = store_results(final_result, 'repomix')
        
        if store_result.is_completed():
            store_data = store_result.result()
            # Extract the MongoDB ObjectID and add to results
            final_result['result_obj_id'] = store_data.db_result
            logger.info(f"Results stored with ID: {store_data.db_result}")
        else:
            # Handle database storage error
            if store_result.result() and hasattr(store_result.result(), 'errors'):
                error_list = store_result.result().errors
                if error_list:
                    # Add error information to final result
                    if 'errors' not in final_result:
                        final_result['errors'] = []
                    elif isinstance(final_result['errors'], str):
                        final_result['errors'] = [final_result['errors']]
                    
                    final_result['errors'].extend(error_list)
                    logger.warning(f"Database storage errors: {', '.join(error_list)}")
        
        # Create a summary markdown artifact
        summary = {
            "repository": task.github_repo_url,
            "analysis_completed": True,
            "result_id": final_result.get('result_obj_id', None),
            "errors": final_result.get('errors', [])
        }
        
        summary_markdown = generic_results_to_markdown(summary)
        create_markdown_artifact(
            markdown=summary_markdown,
            key="repo-analysis-summary",
            description=f"Repository Analysis Summary for {task.github_repo_url}"
        )
        
        return Completed(data=final_result, message="✅ Repository analysis completed successfully")
        
    except Exception as e:
        error_msg = f"Repository analysis flow failed: {str(e)}"
        logger.error(error_msg)
        return Failed(data={"error": str(e)}, message=error_msg)

__all__ = ["run_repo_analysis", "RepoAnalysisTask"]

# if __name__ == "__main__":
    
#     task = RepoAnalysisTask(
#         remote_repo_url="https://github.com/PHOENIXSEC-AI/DeepSeek-V3", 
#         repomix_config_path="/workspaces/workflow-automation/src/tools/repomix/default_repomix_config.json",
#         debug=True
#     )
    
#     run_repo_analysis(task)