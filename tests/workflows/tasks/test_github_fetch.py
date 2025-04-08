"""
Tests for GitHub repository fetching tasks.

This file tests the tasks defined in the github/fetch.py module following
Prefect's best practices for testing tasks.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from prefect import flow
from prefect.testing.utilities import prefect_test_harness
from prefect.states import Completed, Failed
from prefect.exceptions import FailedRun

# Import the module directly for more resilient patching
import workflows.tasks.github.fetch as github_fetch_module
from workflows.tasks.github.fetch import (
    fetch_github_repo,
    fetch_private_github_repo,
    mask_sensitive_value
)


@pytest.fixture(scope="session", autouse=True)
def prefect_test_fixture():
    """Set up Prefect test environment for all tests."""
    with prefect_test_harness():
        yield


# Helper factory to create mocked objects for GitHub fetch tests
def create_github_fetch_test_env(exists=True, mock_token="ghp_1234567890abcdef"):
    """
    Create a test environment with mocked dependencies for GitHub fetch tests.
    
    This factory function creates all necessary mocks for testing GitHub fetch tasks.
    By centralizing the mocking setup, tests become more resilient to refactoring
    and implementation changes.
    
    Args:
        exists (bool): Whether the path should exist after fetch
        mock_token (str): GitHub token to use, or None to test missing token scenario
    
    Returns:
        dict: Dictionary containing all mocked objects needed for tests
    """
    # Create mock path and fetch repository functionality
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = exists
    mock_path_instance.as_uri.return_value = "file:///tmp/repo-path"
    
    mock_path = MagicMock()
    mock_path.return_value = mock_path_instance
    
    # Mock fetcher with customizable behavior
    mock_fetch = MagicMock()
    if exists:
        mock_fetch.return_value = "/tmp/repo-path"
    else:
        mock_fetch.return_value = "/tmp/nonexistent-path"
    
    # Mock app_config
    mock_config = MagicMock()
    mock_config.GITHUB_TOKEN = mock_token
    
    # Mock artifact creation
    mock_artifact = MagicMock()
    
    # Mock logger
    mock_logger = MagicMock()
    
    return {
        "path": mock_path,
        "path_instance": mock_path_instance,
        "fetch": mock_fetch,
        "config": mock_config,
        "artifact": mock_artifact,
        "logger": mock_logger
    }


def test_mask_sensitive_value():
    """Test the mask_sensitive_value function."""
    # Test with a short value
    assert mask_sensitive_value("123") == "****"
    
    # Test with a longer value - fixing the expected number of asterisks
    assert mask_sensitive_value("ghp_1234567890abcdef") == "ghp_************cdef"
    
    # Test with None
    assert mask_sensitive_value(None) == "****"


def test_fetch_github_repo_success():
    """Test fetch_github_repo task with successful execution.
    
    This test uses dynamic import-based patching that's resilient to refactoring.
    """
    # Mock the dependencies by patching the module objects directly
    # This approach is more resilient to refactors that move code between files
    with patch.object(github_fetch_module.fetcher, 'fetch_repository') as mock_fetch, \
        patch.object(github_fetch_module, 'create_link_artifact') as mock_artifact, \
        patch.object(github_fetch_module, 'Path') as mock_path:
        
        # Set up the mocks
        mock_fetch.return_value = "/tmp/repo"
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.as_uri.return_value = "file:///tmp/repo"
        mock_path.return_value = mock_path_instance
        
        # Define a test flow to run the task
        @flow
        def test_flow():
            return fetch_github_repo(github_repo_url="https://github.com/user/repo")
        
        # Run the flow
        result = test_flow()
        
        # Assert the task completed successfully
        assert result.is_completed()
        assert result.result()["result_dir"] == "/tmp/repo"
        
        # Verify the mocks were called with correct arguments
        mock_fetch.assert_called_once_with(repo_url="https://github.com/user/repo")
        mock_artifact.assert_called_once()


def test_fetch_github_repo_failure_path_not_exists():
    """Test fetch_github_repo task with failure when path doesn't exist."""
    # Mock the dependencies
    with patch('workflows.tasks.github.fetch.fetcher.fetch_repository') as mock_fetch, \
        patch('workflows.tasks.github.fetch.Path') as mock_path, \
        patch('workflows.tasks.github.fetch.logger.debug') as mock_logger:
        
        # Set up the mocks
        mock_fetch.return_value = "/tmp/nonexistent_repo"
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        # For testing a failure, it's better to test the function directly
        # rather than using a flow, since flow failures can be harder to handle
        result = fetch_github_repo.fn(github_repo_url="https://github.com/user/repo")
        
        # Assert the task failed as expected
        assert result.is_failed()
        assert "returned invalid path" in result.message


def test_fetch_github_repo_exception():
    """Test fetch_github_repo task with an exception during execution."""
    # Mock the dependencies
    with patch('workflows.tasks.github.fetch.fetcher.fetch_repository') as mock_fetch, \
        patch('workflows.tasks.github.fetch.logger.debug') as mock_logger:
        
        # Set up the mock to raise an exception
        mock_fetch.side_effect = Exception("Repository not found")
        
        # For testing a failure, it's better to test the function directly
        result = fetch_github_repo.fn(github_repo_url="https://github.com/user/nonexistent")
        
        # Assert the task failed as expected
        assert result.is_failed()
        assert "Repository not found" in result.message


def test_fetch_private_github_repo_success():
    """Test fetch_private_github_repo task with successful execution."""
    # Use the test environment factory to create mocks
    mocks = create_github_fetch_test_env(exists=True, mock_token="ghp_1234567890abcdef")
    
    # Set up the test environment
    with patch.object(github_fetch_module.fetcher, 'fetch_repository', mocks["fetch"]), \
         patch.object(github_fetch_module, 'create_link_artifact', mocks["artifact"]), \
         patch.object(github_fetch_module, 'Path', mocks["path"]), \
         patch.object(github_fetch_module, 'app_config', mocks["config"]), \
         patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_1234567890abcdef"}):
        
        # Define a test flow to run the task
        @flow
        def test_flow():
            return fetch_private_github_repo(github_repo_url="https://github.com/user/private-repo")
        
        # Run the flow
        result = test_flow()
        
        # Assert the task completed successfully
        assert result.is_completed()
        assert result.result()["result_dir"] == "/tmp/repo-path"
        
        # Verify the mocks were called with correct arguments
        mocks["fetch"].assert_called_once_with(
            repo_url="https://github.com/user/private-repo",
            token="ghp_1234567890abcdef"
        )
        mocks["artifact"].assert_called_once()


def test_fetch_private_github_repo_missing_token():
    """Test fetch_private_github_repo task with missing GitHub token.
    
    This test uses a dynamic approach that's resilient to implementation changes.
    """
    # Create a test environment with no token
    mocks = create_github_fetch_test_env(mock_token=None)
    
    # Set up the test environment with extensive patching
    # This ensures we control all parts of the environment that might be accessed
    with patch.object(github_fetch_module, 'app_config', mocks["config"]), \
         patch.dict(os.environ, {}, clear=True), \
         patch.object(github_fetch_module.fetcher, 'fetch_repository', mocks["fetch"]):
        
        # Ensure we're testing the function's validation, not just its happy path
        with pytest.raises(AssertionError) as excinfo:
            fetch_private_github_repo.fn(github_repo_url="https://github.com/user/private-repo")
        
        # Verify that the assertion error contains the expected message
        assert "Github Token is required" in str(excinfo.value)
        
        # Verify that fetch_repository was never called (assertion prevented it)
        mocks["fetch"].assert_not_called()


def test_fetch_github_repo_fn():
    """Test the underlying function of fetch_github_repo task directly."""
    # Use the test environment factory
    mocks = create_github_fetch_test_env(exists=True)
    
    # Mock the dependencies - using object patching for resilience
    with patch.object(github_fetch_module.fetcher, 'fetch_repository', mocks["fetch"]), \
         patch.object(github_fetch_module, 'create_link_artifact', mocks["artifact"]), \
         patch.object(github_fetch_module, 'Path', mocks["path"]):
        
        # Call the task function directly
        result = fetch_github_repo.fn(github_repo_url="https://github.com/user/repo")
        
        # When testing the function directly, we can inspect the return value directly
        assert hasattr(result, 'is_completed') and result.is_completed()
        assert result.data["result_dir"] == "/tmp/repo-path" 

if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", __file__]) 