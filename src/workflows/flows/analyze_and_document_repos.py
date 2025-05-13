import os
import click
import asyncio
from typing import Union, Dict, Any, List, Optional

from prefect import flow
from prefect.states import Failed, Completed

from workflows.flows.doc_gen import run_generate_docs_new
from workflows.flows.private_repo_analysis import run_private_repo_analysis

from workflows.flows.repo_analysis import run_repo_analysis
from workflows.agents.models import AgentAnalysisResult, AgentBatchResult
from workflows.flows.extraction_strategies import security_review, add_basev2, merge_strategy_results

from core.config import app_config
from core.utils import LoggerFactory
from core.models import RepoAnalysisTask, RepoAnalysisResult, RepomixResultData
from core.services.database import AsyncRepository, AsyncWorkflowStorage

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

local_storage = AsyncWorkflowStorage(db_path=app_config.get_db_path())

DEFAULT_REPOMIX_CONFIG_PATH = os.environ.get(
    "DEFAULT_REPOMIX_CONFIG_PATH",
    "/workspaces/workflow-automation/src/tools/repomix/default_repomix_config.json"
)

def flow_precheck() -> Union[bool, str]:
    """
    Verify required environment variables and prerequisites for the flow.
    
    Checks if the GITHUB_TOKEN environment variable is available, which is
    required for authenticating with GitHub to access private repositories.
    
    Returns:
        A tuple containing:
            - bool: True if all prerequisites are met, False otherwise
            - str: Empty string if successful, or error message if failed
    """
    # Check for GitHub token in environment
    if "GITHUB_TOKEN" not in os.environ:
        flow_msg = """❌ GITHUB_TOKEN environment variable is required for private repository access
        
        Please set it using:
            export GITHUB_TOKEN=ghp_your_token_here
        OR
            In .env file
        """
        logger.error(flow_msg)
        return False, flow_msg
    
    logger.debug("✅ Using GitHub token from environment variables")
    return True, ""

def build_repo_result(
    repo_url: str, 
    status: str = "failed", 
    error: Optional[str] = None, 
    result: Optional[Any] = None, 
    result_obj_id: Optional[str] = None,
    documentation_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Helper function to build a standardized repository result entry.
    
    Args:
        repo_url: The URL of the repository
        status: The status of the processing (success/failed)
        error: Optional error message if status is failed
        result: Optional result data if status is success
        result_obj_id: Optional MongoDB ObjectId of the repository analysis document
        documentation_path: Optional path to the generated documentation
        
    Returns:
        Dictionary containing the standardized result entry
    """
    return {
        "repository_url": repo_url,
        "status": status,
        "error": error,
        "result": result,
        "result_obj_id": result_obj_id,
        "documentation_path": documentation_path if status == "success" else None
    }

def is_valid_github_url(url: str) -> bool:
    """Validate that a URL is a properly formatted GitHub repository URL."""
    import re
    pattern = r'^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$'
    return bool(re.match(pattern, url))

async def _analyze_repo(github_url:str, repomix_config_path:str=DEFAULT_REPOMIX_CONFIG_PATH, is_private:bool=False) -> RepoAnalysisResult:
    
    final_result = None
    repo_analysis_result = None
    
    if github_url and is_valid_github_url(github_url):
        task = RepoAnalysisTask(
            github_repo_url=github_url,
            repomix_config_path=repomix_config_path
        )
        
        if is_private:
            repo_analysis_result = run_private_repo_analysis(task)
        else:
            repo_analysis_result = run_repo_analysis(task)
    
        if not repo_analysis_result:
            logger.warning(f"Failed to run repository analysis for {github_url}")
            
            return RepoAnalysisResult(repository_url=github_url,error="Failed to run repository analysis")
        
        # Where repo files are stored?
        result_local_path = repo_analysis_result.get('local_repo_path', None)
        
        if not result_local_path:
            logger.error(f"Error: repo_analysis_result is missing `local_repo_path` for {github_url} analysis")
            
            return RepoAnalysisResult(
                repository_url=github_url,
                error="Missing result local_path from repository analysis"
            )
        
        final_result = RepoAnalysisResult(
            repository_url=github_url,
            status="success",
            error=None,
            result=repo_analysis_result,
            result_path=result_local_path
        )
    
    return final_result

@flow(
    log_prints=True, 
    name="run_analyze_and_document_repos", 
    description="Run full analysis of multiple private repos with the same configuration",
)
async def run_analyze_and_document_repos(
    github_repo_urls: List[str],
    repomix_config_path: str = DEFAULT_REPOMIX_CONFIG_PATH,
    is_private: bool = False,
) -> Union[Completed,Failed]:
    """
    Run analysis, enrichment, and documentation generation for multiple repositories
    using the same configuration.
    
    This flow processes each repository in sequence:
    1. Runs the private repo analysis flow to analyze the repository
    2. Extracts base information (env vars, APIs, DB connections) with AI
    3. Merges the AI results into the MongoDB document
    4. Generates markdown documentation
    
    Error handling is done per-repository, allowing the flow to continue
    even if one repository fails, with detailed status reporting.
    
    Args:
        github_repo_urls: List of GitHub repository URLs to analyze. If not provided,
                        defaults to a single example repository.
        repomix_config_path: Path to the Repomix configuration file to use for all repositories
        is_private: Flag if private repo analysis should be runned istead of public
    Returns:
        A consolidated Prefect state with:
        - status: success if at least one repository was processed successfully
        - data: list of results for each repository with individual status
        
    Examples:
        >>> # Analyze a single repository
        >>> await run_enrich_documents(github_repo_urls=["https://github.com/org/repo"])
        
        >>> # Analyze multiple repositories with the same configuration
        >>> await run_enrich_documents(
        ...     github_repo_urls=[
        ...         "https://github.com/org/repo1",
        ...         "https://github.com/org/repo2"
        ...     ],
        ...     repomix_config_path="/path/to/config.json"
        ... )
    """
    logger.info(f"Starting repository analysis and documentation flow for {len(github_repo_urls)} repositories")
    
    # Default repository if none provided
    if not github_repo_urls:
        raise ValueError(f"Param github_repo_urls is required for run_codebase_analysis_and_documentation flow")
    
    if is_private:
        # Check prerequisites
        can_run, err_msg = flow_precheck()
        if not can_run:
            return Failed(err_msg)
    
    # Track results for each repository
    consolidated_results = []
    # Place to store repository file content and metadata
    repomix_result_store = AsyncRepository(model_class=RepomixResultData, storage=local_storage)
    
    # Process each repository
    for repo_url in github_repo_urls:
        if not is_valid_github_url(repo_url):
            logger.warning(f"Skipping invalid GitHub URL format: {repo_url}")
            
            consolidated_results.append(
                RepoAnalysisResult(
                    repository_url=repo_url,
                    error="Invalid GitHub repository URL format"
                )
            )
            continue
        
        logger.info(f"Processing repository: {repo_url}")
        tool_run_result = None
        
        # Stage 1: Running Repomix tool to analyze repository and store results
        try:
            tool_run_result = await _analyze_repo(github_url=repo_url,repomix_config_path=repomix_config_path, is_private=is_private)
        
        except Exception as ex:
            err_msg = f"Error: failed to analyze repository: {repo_url}: {str(ex)}. Skipping..."
            logger.error(err_msg)
            
            consolidated_results.append(
                RepoAnalysisResult(
                    repository_url=repo_url,
                    error=err_msg
                )
            )
            continue # Continue processing other repos
        finally:
            if tool_run_result:
                tool_run_result_data = getattr(tool_run_result,'result', None)
                
                if tool_run_result_data:
                    # Using nested try/except to catch db errors
                    try:
                        logger.info(f"Storing private repo analysis results to local data store")
                        doc_id = await repomix_result_store.create(tool_run_result_data)
                        logger.debug(f"DONE: DB Location: {app_config.get_db_path()}, doc_id: {doc_id}")
                    except Exception as ex:
                        err_msg = f"Error: Failed to store repo analysis results. Reason: {str(ex)}"
                        continue
                else:
                    err_msg = f"Error: Failed to store analysis results. Either tool_run_result is missing `result` attribute or it's value is None. Skipping..."
                    logger.error(err_msg)
                    continue # Continue processing other repose, cause this failed
            else:
                err_msg = f"Error: Either public/private repo analysis returned no result. Did tool failed to analyze repo? Skipping..."
                logger.error(err_msg)     
                continue
        
        # Stage 2: Applying strategies (extending analysis phase)
        try:
            if tool_run_result:
                results_to_be_merged = []
                base_result_data = {}
                logger.info(f"Running Base Extraction Strategy")
                # Run Base Information Extraction Strategy Flow to get env, api, db constants
                base_result_data = await add_basev2(repomix_result=tool_run_result)
                
                # logger.info(f"Running Security Review Strategy")
                # appsec_result_data = await security_review(repomix_result=tool_run_result)
                
                # Additional strategies goes here
                
                if not base_result_data:
                    raise Exception(f"add_base returned empty object")

                # Results from additional strategies should be included here
                results_to_be_merged.extend([base_result_data,])
            else:
                raise ValueError(f"Error: Enhanced Analysis completed but result is None. Skipping...")
            
        except Exception as ex:
            err_msg = f"Uncaught Exception when trying to apply repo analysis strategies: {str(ex)}"
            logger.error(err_msg)
            
            consolidated_results.append(
                RepoAnalysisResult(
                    repository_url=repo_url,
                    error=err_msg
                )
            )
            continue
        
        # Stage 3: Merging results from strategies into final result object
        try:
            if results_to_be_merged:
                local_storage_id = doc_id[0] if doc_id else '' # We will replace original doc, with enriched one
                org_result_data = getattr(tool_run_result, 'result', None)
                org_files = getattr(org_result_data, 'files', [])
                # Ensure we have valid data to work with
                if not org_result_data:
                    logger.warning("Original result data is missing or invalid")
                    consolidated_results.append(
                        RepoAnalysisResult(
                            repository_url=repo_url,
                            error="Original result data is missing or invalid"
                        )
                    )
                    continue
                
                merge_strategy_results(org_files, results_to_be_merged)
                
                setattr(org_result_data,'files',org_files)
                
                # Update the document in storage with merged data
                update_success = await repomix_result_store.update_document_with_merged_data(
                    local_storage_id, 
                    org_result_data
                )
                
                consolidated_results.append(
                    RepoAnalysisResult(
                        repository_url=repo_url,
                        result=org_result_data,
                        error=None
                    )
                )
            else:
                logger.warning(f"No strategy results to merge for repository {repo_url}")
                consolidated_results.append(
                    RepoAnalysisResult(
                        repository_url=repo_url,
                        result=org_result_data,
                        error=None
                    )
                )
        except Exception as ex:
            err_msg = f"Error merging strategy results for repository {repo_url}: {str(ex)}"
            logger.error(err_msg)
            
            consolidated_results.append(
                RepoAnalysisResult(
                    repository_url=repo_url,
                    error=err_msg
                )
            )
        
        # Stage 4: Creating Docs
        try:
            doc_path = await run_generate_docs_new(build_from_obj=org_result_data)
        except Exception as ex:
            pass
        logger.info(f"Successfully processed repository: {repo_url}")
    
    return Completed(
        message=f"Successfully processed of {len(consolidated_results)} repositories",
        data=consolidated_results
    )

@click.command()
@click.option(
    "--urls",
    multiple=True,
    help="GitHub repository URLs to analyze"
)
@click.option(
    "--urls-file",
    type=str,
    help="Path to a file containing GitHub repository URLs (one URL per line)"
)
@click.option(
    "--repomix-config",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    default="src/tools/repomix/all_languages_repomix_config.json",
    help="Path to the Repomix configuration file"
)
@click.option(
    "--private",
    default=False,
    help="Whether repositories are private (requires GITHUB_TOKEN)"
)
def main(urls, urls_file, repomix_config, private):
    """Run analysis and documentation generation for GitHub repositories."""
    import asyncio
    
    # Get GitHub URLs
    github_repos_to_process = list(urls)
    
    # Read from urls-file if provided and exists
    if urls_file:
        try:
            with open(urls_file, 'r') as url_file:
                file_urls = [url.replace('\n','').replace(',','').strip() for url in url_file.readlines()]
                github_repos_to_process.extend(file_urls)
        except FileNotFoundError:
            click.echo(f"Warning: URLs file '{urls_file}' not found, ignoring it.")
    
    # If no URLs provided, fall back to default behavior (sample_repos.txt)
    if not github_repos_to_process:
        try:
            with open('sample_repos.txt', 'r') as url_file:
                github_repos_to_process = [url.replace('\n','').replace(',','').strip() for url in url_file.readlines()]
            logger.info(f"No URLs provided. Using {len(github_repos_to_process)} URLs from sample_repos.txt")
        except FileNotFoundError:
            click.echo("Error: No GitHub repository URLs provided and sample_repos.txt not found.")
            click.echo("Please use --urls or --urls-file, or create a sample_repos.txt file.")
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            ctx.exit(1)
    
    asyncio.run(
        run_analyze_and_document_repos(
            github_repo_urls=github_repos_to_process,
            repomix_config_path=repomix_config,
            is_private=private
        )
    )


if __name__ == "__main__":
    main()