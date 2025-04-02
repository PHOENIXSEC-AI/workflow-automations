from typing import Optional
from prefect.input import RunInput

class RepoAnalysisTask(RunInput):
    """
    Input parameters for the private repository analysis flow.
    
    Note:
        This flow requires the GITHUB_TOKEN environment variable to be set with a valid
        GitHub personal access token (starting with 'ghp_').
    
    Attributes:
        github_repo_url: URL of the private GitHub repository to analyze
        repomix_config_path: Path to the Repomix configuration file
        output_path: Optional custom path for analysis output
    """
    github_repo_url: str
    repomix_config_path: str
    output_path: Optional[str] = None

__all__ = ["RepoAnalysisTask"]