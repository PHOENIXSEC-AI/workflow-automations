"""
GitHub repository fetching tasks.
"""
from pathlib import Path
import os
from prefect import task

from prefect.states import Completed, Failed
from prefect.artifacts import create_link_artifact

from core.services import CodebaseFetcher
from core.utils.logger import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

fetcher = CodebaseFetcher()
# Function to mask sensitive values
def mask_sensitive_value(value):
    """
    Mask a sensitive value by showing only the first 4 and last 4 characters,
    with asterisks in between.
    """
    if value and len(value) > 8:
        return value[:4] + '*' * (len(value) - 8) + value[-4:]
    return '****'


@task(name="fetch_private_github_repo")
def fetch_private_github_repo(github_repo_url: str):
    # Get GitHub token from settings or environment variable
    github_token = app_config.GITHUB_TOKEN or os.environ.get("GITHUB_TOKEN")
    
    assert (
        github_token is not None and "ghp_" in github_token
    ), "Github Token is required for private repos. Set it in the GITHUB_TOKEN environment variable."

    task_run_msg = ""
    masked_gh_token = mask_sensitive_value(github_token)
    
    try:
        result_dir = fetcher.fetch_repository(
            repo_url=github_repo_url, token=github_token
        )

        result_dir_path = Path(result_dir)

        if result_dir_path.exists():
            task_run_msg = f"OK: fetch_repository(url={github_repo_url},token={masked_gh_token})"
            
            create_link_artifact(
                key="fetch-gh-result-dir",
                link=result_dir_path.as_uri(),
                description="## Link to the fetched repository on disk",
            )
            
            return Completed(data={"result_dir": result_dir}, message=task_run_msg)
        else:
            raise Exception(
                f"fetch_repository(url={github_repo_url},token={masked_gh_token}) returned invalid path: {result_dir}"
            )
    except Exception as e:
        task_run_msg= f"Error: {str(e)}"
        logger.debug(task_run_msg)

    return Failed(message=task_run_msg)

@task(name="fetch_github_repo")
def fetch_github_repo(github_repo_url: str):
    task_run_msg = ""

    try:
        result_dir = fetcher.fetch_repository(repo_url=github_repo_url)

        result_dir_path = Path(result_dir)

        if result_dir_path.exists():
            task_run_msg = f"OK: fetch_repository(url={github_repo_url})"
            
            create_link_artifact(
                key="fetch-gh-result-dir",
                link=result_dir_path.as_uri(),
                description="## Link to the fetched repository on disk",
            )
            
            return Completed(data={"result_dir": result_dir}, message=task_run_msg)
        else:
            raise Exception(
                f"fetch_repository(url={github_repo_url}) returned invalid path: {result_dir}"
            )
    except Exception as e:
        task_run_msg= f"Error: {str(e)}"
        logger.debug(task_run_msg)

    
    return Failed(message=task_run_msg)

__all__ = ["fetch_github_repo", "fetch_private_github_repo"] 