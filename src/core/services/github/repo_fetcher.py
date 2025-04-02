import os
import shutil

from uuid import uuid4
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from core.config import app_config
from core.utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

TMP_DATA_BASE = "/tmp/a78adba6599a44d1bf092cc0f92c52ee"


class CodebaseFetcher:
    """
    A tool for fetching GitHub repositories and storing them locally.
    Supports both public and private repositories with token authentication.
    """

    @staticmethod
    def _create_workdir() -> Path:
        """
        Create a temporary directory with a unique identifier.

        Returns:
            Path: Path object pointing to the created temporary directory

        Raises:
            OSError: If directory creation fails
        """
        try:
            # Generate unique identifier
            dir_id = uuid4().hex

            # Create the full path
            temp_path = Path(TMP_DATA_BASE) / dir_id

            # Create the directory
            os.makedirs(temp_path, exist_ok=True)
            logger.debug(f"Created temporary directory: {temp_path}")

            return temp_path

        except PermissionError as e:
            logger.error(
                f"Permission denied when creating temporary directory: {e}")
            raise OSError(
                f"Cannot create temporary directory due to permission issues: {e}")

        except OSError as e:
            logger.error(f"Failed to create temporary directory: {e}")
            raise OSError(f"Failed to create temporary directory: {e}")

    def _get_auth_kwargs(self, repo_url, token=None):
        """
        Prepare authentication keyword arguments for GitPython based on the repository URL and token.

        Args:
            repo_url (str): GitHub repository URL or identifier
            token (str, optional): GitHub personal access token for private repositories

        Returns:
            dict: Keyword arguments for GitPython's clone_from method
        """
        clone_kwargs = {}

        # If no token provided, return empty kwargs
        if not token:
            return clone_kwargs

        # Handle authentication for private repositories
        # GitPython supports environment-based authentication
        # This is more secure than embedding the token in the URL

        # For HTTPS URLs
        if repo_url.startswith('https://') or not any(x in repo_url for x in ['github.com', 'git@github.com']):
            # Create a minimal environment with only the necessary variables
            env = {
                'GIT_ASKPASS': 'echo',
                'GIT_USERNAME': 'git',
                'GIT_PASSWORD': token
            }

            # Add PATH if needed for git executable
            if 'PATH' in os.environ:
                env['PATH'] = os.environ['PATH']

            clone_kwargs['env'] = env
            logger.debug(
                "Using token authentication via minimal environment variables")

        # For SSH URLs, token is not used directly
        elif repo_url.startswith('git@'):
            logger.debug("SSH URL detected, token will not be used")

        return clone_kwargs

    def _normalize_github_url(self, repo_url, token=None):
        """
        Normalize GitHub repository URL to ensure it's in the correct format.
        If token is provided, embeds it directly in the URL for authentication.

        Args:
            repo_url (str): GitHub repository URL or identifier
            token (str, optional): GitHub personal access token for private repositories

        Returns:
            tuple: (normalized_url, repo_name)
        """
        # Extract owner and repo name from various formats

        # Format: owner/repo
        if '/' in repo_url and not any(x in repo_url for x in ['github.com', 'git@github.com']):
            owner, repo = repo_url.split('/')
            normalized_url = f"https://github.com/{owner}/{repo}.git"
            repo_name = repo

        # Format: https://github.com/owner/repo
        elif 'github.com/' in repo_url and not repo_url.endswith('.git'):
            parts = repo_url.split('github.com/')
            owner_repo = parts[1]
            if owner_repo.endswith('/'):
                owner_repo = owner_repo[:-1]
            owner, repo = owner_repo.split('/')
            normalized_url = f"https://github.com/{owner}/{repo}.git"
            repo_name = repo

        # Format: https://github.com/owner/repo.git
        elif 'github.com/' in repo_url and repo_url.endswith('.git'):
            parts = repo_url.split('github.com/')
            owner_repo = parts[1]
            owner, repo_with_git = owner_repo.split('/')
            repo = repo_with_git.replace('.git', '')
            normalized_url = f"https://github.com/{owner}/{repo}.git"
            repo_name = repo

        # Format: git@github.com:owner/repo.git
        elif repo_url.startswith('git@github.com:'):
            parts = repo_url.split('git@github.com:')
            owner_repo = parts[1]
            owner, repo_with_git = owner_repo.split('/')
            repo = repo_with_git.replace('.git', '')
            normalized_url = f"https://github.com/{owner}/{repo}.git"
            repo_name = repo

        else:
            raise ValueError(f"Unsupported GitHub URL format: {repo_url}")

        # If token is provided, insert it directly into the URL
        if token and normalized_url.startswith('https://github.com/'):
            normalized_url = normalized_url.replace(
                'https://github.com/', f'https://{token}:x-oauth-basic@github.com/')
            logger.debug(
                "Token embedded directly in the URL for authentication")

        return normalized_url, repo_name

    def fetch_repository(self, repo_url, token=None):
        """
        Fetch a GitHub repository and store it locally, downloading files directly into 
        the working directory without creating a subdirectory for the repository.

        Args:
            repo_url (str): GitHub repository URL or identifier
            token (str, optional): GitHub personal access token for private repositories

        Returns:
            str: Path to the cloned repository

        Raises:
            ValueError: If the repository URL format is unsupported
            OSError: If the temporary directory cannot be created
            GitCommandError: If the repository cannot be cloned
        """
        # Normalize the GitHub URL with token if provided
        try:
            normalized_url, repo_name = self._normalize_github_url(
                repo_url, token)
            logger.debug(
                f"Normalized URL: {normalized_url.replace(token, '***') if token else normalized_url}, Repository name: {repo_name}")
        except ValueError as e:
            logger.error(f"Failed to normalize repository URL: {e}")
            raise

        # Location where fetched repository files are stored
        tmp_data_storage = self._create_workdir()

        assert tmp_data_storage is not None, "Failed to create tmp workdir for file storage, did you initialize the CodebaseFetcher?"

        try:
            logger.debug(f"Cloning repository from {repo_url}")

            # Prepare the URL for GitPython
            clone_url = normalized_url

            assert clone_url is not None and 'github.com' in clone_url, f"Failed to normalize github repo url: {repo_url}"

            # Prepare authentication 
            auth_kwargs = self._get_auth_kwargs(repo_url, token)

            # Clone the repository to a temporary location
            Repo.clone_from(clone_url, tmp_data_storage, **auth_kwargs)
            logger.debug(f"Repository cloned to {tmp_data_storage}")

            return str(tmp_data_storage)

        except GitCommandError as e:
            try:
                # Clean up failed clone attempt
                if os.path.exists(tmp_data_storage):
                    shutil.rmtree(tmp_data_storage)
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up repository directory after failed clone: {cleanup_error}")

            if 'Authentication failed' in str(e):
                logger.error(
                    f"Authentication failed when cloning repository: {e}")
                raise ValueError(
                    "Authentication failed. Please check your token or repository permissions.")
            elif 'not found' in str(e):
                logger.error(f"Repository not found: {e}")
                raise ValueError(
                    f"Repository '{repo_url}' not found. Please check the URL and your access permissions.")
            else:
                logger.error(f"Failed to clone repository: {e}")
                raise GitCommandError(
                    f"Failed to clone repository: {e}", e.status, e.stderr)

        except Exception as e:
            logger.error(f"Unexpected error while fetching repository: {e}")
            # Clean up on other exceptions
            try:
                if os.path.exists(tmp_data_storage):
                    shutil.rmtree(tmp_data_storage)
            except Exception:
                pass
            raise 