"""
Service for interacting with GitHub repositories.
"""
from typing import Optional

from core.utils.logger import LoggerFactory
from .repo_fetcher import CodebaseFetcher

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

class RepositoryService:
    """
    Service for interacting with GitHub repositories.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the repository service.
        
        Args:
            token: Optional GitHub authentication token
        """
        self.fetcher = CodebaseFetcher()
        self.token = token
    
    def fetch_repository(self, repo_url: str) -> str:
        """
        Fetch a public repository.
        
        Args:
            repo_url: The URL of the GitHub repository to fetch
        
        Returns:
            String path to the fetched repository on disk
        """
        logger.info(f"Fetching public repository: {repo_url}")
        return self.fetcher.fetch_repository(repo_url=repo_url)
    
    def fetch_private_repository(self, repo_url: str, token: Optional[str] = None) -> str:
        """
        Fetch a private repository using a token.
        
        Args:
            repo_url: The URL of the GitHub repository to fetch
            token: Optional token override for this specific request
        
        Returns:
            String path to the fetched repository on disk
            
        Raises:
            ValueError: If no token is provided
        """
        auth_token = token or self.token
        if not auth_token:
            raise ValueError("GitHub token is required for private repositories")
            
        logger.info(f"Fetching private repository: {repo_url}")
        return self.fetcher.fetch_repository(repo_url=repo_url, token=auth_token) 