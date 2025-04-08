"""
Tests for the GitHub Repository Service.

This module tests the functionality of the RepositoryService class
which is responsible for interacting with GitHub repositories.
"""
import pytest
from unittest.mock import MagicMock, patch

from core.services.github.repository_service import RepositoryService
from core.services.github.repo_fetcher import CodebaseFetcher


class TestRepositoryService:
    """Test suite for the RepositoryService class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock for the CodebaseFetcher
        self.mock_fetcher = MagicMock(spec=CodebaseFetcher)
        
        # Setup the mock return value for fetch_repository
        self.mock_fetcher.fetch_repository.return_value = "/path/to/fetched/repo"
        
        # Patch the CodebaseFetcher in the repository_service module
        self.fetcher_patcher = patch('core.services.github.repository_service.CodebaseFetcher')
        self.mock_fetcher_class = self.fetcher_patcher.start()
        self.mock_fetcher_class.return_value = self.mock_fetcher
    
    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        self.fetcher_patcher.stop()
    
    def test_init_without_token(self):
        """Test initialization without a token."""
        service = RepositoryService()
        
        # Verify the CodebaseFetcher was created
        assert self.mock_fetcher_class.called
        
        # Verify the token is None
        assert service.token is None
    
    def test_init_with_token(self):
        """Test initialization with a token."""
        token = "github_token_123"
        service = RepositoryService(token=token)
        
        # Verify the CodebaseFetcher was created
        assert self.mock_fetcher_class.called
        
        # Verify the token was stored
        assert service.token == token
    
    def test_fetch_repository(self):
        """Test fetching a public repository."""
        service = RepositoryService()
        repo_url = "https://github.com/username/repo"
        
        result = service.fetch_repository(repo_url)
        
        # Verify the fetcher method was called with correct parameters
        self.mock_fetcher.fetch_repository.assert_called_once_with(repo_url=repo_url)
        
        # Verify the result is as expected
        assert result == "/path/to/fetched/repo"
    
    def test_fetch_private_repository_with_init_token(self):
        """Test fetching a private repository using the token provided during initialization."""
        token = "github_token_123"
        service = RepositoryService(token=token)
        repo_url = "https://github.com/username/private-repo"
        
        result = service.fetch_private_repository(repo_url)
        
        # Verify the fetcher method was called with correct parameters
        self.mock_fetcher.fetch_repository.assert_called_once_with(repo_url=repo_url, token=token)
        
        # Verify the result is as expected
        assert result == "/path/to/fetched/repo"
    
    def test_fetch_private_repository_with_method_token(self):
        """Test fetching a private repository with token override at method level."""
        init_token = "github_token_123"
        method_token = "github_token_override"
        
        service = RepositoryService(token=init_token)
        repo_url = "https://github.com/username/private-repo"
        
        result = service.fetch_private_repository(repo_url, token=method_token)
        
        # Verify the fetcher method was called with the overridden token
        self.mock_fetcher.fetch_repository.assert_called_once_with(repo_url=repo_url, token=method_token)
        
        # Verify the result is as expected
        assert result == "/path/to/fetched/repo"
    
    def test_fetch_private_repository_without_token(self):
        """Test that an error is raised when fetching a private repository without a token."""
        service = RepositoryService()  # No token
        repo_url = "https://github.com/username/private-repo"
        
        # Verify that a ValueError is raised
        with pytest.raises(ValueError) as excinfo:
            service.fetch_private_repository(repo_url)
        
        # Verify the error message
        assert "GitHub token is required for private repositories" in str(excinfo.value)
        
        # Verify that fetch_repository was never called
        self.mock_fetcher.fetch_repository.assert_not_called()


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 