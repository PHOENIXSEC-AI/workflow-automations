"""
Tests for workflow tasks defined in tool_repomix.py.

This file tests the tasks defined in the tool_repomix module following
Prefect's best practices for testing tasks.
"""
import pytest
from unittest.mock import patch, MagicMock

from prefect import flow
from prefect.testing.utilities import prefect_test_harness
from prefect.states import Completed, Failed

# Import the module directly for more resilient patching
import workflows.tasks.tool_repomix as tool_repomix_module
from workflows.tasks.tool_repomix import (
    analyze_remote_repo,
    analyze_local_repo,
    parse_tool_results
)


@pytest.fixture(scope="session", autouse=True)
def prefect_test_fixture():
    """Set up Prefect test environment for all tests."""
    with prefect_test_harness():
        yield


def test_analyze_remote_repo_success():
    """Test analyze_remote_repo task with successful execution."""
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'run_repomix') as mock_run_repomix, \
         patch.object(tool_repomix_module, 'create_markdown_artifact') as mock_artifact:
        
        # Set up the mock to return a successful result
        mock_run_repomix.return_value = (0, "/path/to/output.xml", None)
        
        # Define a test flow to run the task
        @flow
        def test_flow():
            return analyze_remote_repo(
                remote_url="https://github.com/test/repo",
                config_path="/path/to/config.json",
                result_path="/path/to/result.xml"
            )
        
        # Run the flow
        result = test_flow()
        
        # Assert the task completed successfully
        assert result.is_completed()
        assert result.result()["repo_url"] == "https://github.com/test/repo"
        assert result.result()["return_code"] == 0
        assert result.result()["output_path"] == "/path/to/output.xml"
        assert result.result()["stderr"] is None
        
        # Verify the mock was called with correct arguments
        mock_run_repomix.assert_called_once_with(
            "https://github.com/test/repo",
            "/path/to/config.json",
            "/path/to/result.xml"
        )
        
        # Verify artifact creation was called
        mock_artifact.assert_called_once()


def test_analyze_remote_repo_failure():
    """Test analyze_remote_repo task with failure execution."""
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'run_repomix') as mock_run_repomix, \
         patch.object(tool_repomix_module, 'create_markdown_artifact') as mock_artifact:
        
        # Set up the mock to return an error
        mock_run_repomix.return_value = (1, None, "Error: Repository not found")
        
        # Call the function directly instead of through a flow
        result = analyze_remote_repo.fn(
            remote_url="https://github.com/nonexistent/repo",
            config_path="/path/to/config.json",
            result_path="/path/to/result.xml"
        )
        
        # Assert the task failed as expected
        assert result.is_failed()
        assert result.data["repo_url"] == "https://github.com/nonexistent/repo"
        assert result.data["return_code"] == 1
        assert result.data["stderr"] == "Error: Repository not found"
        assert "Error: Repository not found" in result.message


def test_analyze_local_repo_success():
    """Test analyze_local_repo task with successful execution."""
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'run_repomix_local') as mock_run_repomix_local, \
         patch.object(tool_repomix_module, 'create_markdown_artifact') as mock_artifact:
        
        # Set up the mock to return a successful result
        mock_run_repomix_local.return_value = (0, "/path/to/output.xml", None)
        
        # Define a test flow to run the task
        @flow
        def test_flow():
            return analyze_local_repo(
                local_repo_path="/path/to/local/repo",
                config_path="/path/to/config.json",
                result_path="/path/to/result.xml"
            )
        
        # Run the flow
        result = test_flow()
        
        # Assert the task completed successfully
        assert result.is_completed()
        assert result.result()["repo_path"] == "/path/to/local/repo"
        assert result.result()["return_code"] == 0
        assert result.result()["output_path"] == "/path/to/output.xml"
        assert result.result()["stderr"] is None
        
        # Verify the mock was called with correct arguments
        mock_run_repomix_local.assert_called_once_with(
            "/path/to/local/repo",
            "/path/to/config.json",
            "/path/to/result.xml"
        )
        
        # Verify artifact creation was called
        mock_artifact.assert_called_once()


def test_parse_tool_results_success():
    """Test parse_tool_results task with successful execution."""
    # Set up the mock result to return
    sample_result = {"result": "success", "data": "sample data"}
    
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'RepoMixParser') as MockRepoMixParser, \
         patch.object(tool_repomix_module, 'repomix_results_to_markdown') as mock_markdown, \
         patch.object(tool_repomix_module, 'create_markdown_artifact') as mock_artifact:
        
        # Set up a proper mock parser instance with a parse method that returns our sample result
        mock_parser_instance = MagicMock()
        MockRepoMixParser.parse = MagicMock(return_value=sample_result)
        
        # Make sure to return a string from the markdown formatter to avoid validation errors
        mock_markdown.return_value = "Formatted markdown content"
        
        # Call the function directly instead of through a flow
        result = parse_tool_results.fn(result_path="/path/to/result.xml")
        
        # Assert the task completed successfully
        assert result.is_completed()
        assert result.data == sample_result
        
        # Verify the mock was called with correct arguments
        MockRepoMixParser.parse.assert_called_once_with(file_path="/path/to/result.xml")
        
        # Verify artifact creation was called
        mock_artifact.assert_called_once()


def test_parse_tool_results_failure():
    """Test parse_tool_results task with failure execution."""
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'RepoMixParser') as MockRepoMixParser, \
         patch.object(tool_repomix_module, 'repomix_results_to_markdown') as mock_markdown:
        
        # Set up the mock parser to return None (failure)
        MockRepoMixParser.parse = MagicMock(return_value=None)
        
        # Not needed for failure case since it doesn't get this far
        mock_markdown.return_value = "Formatted markdown content"
        
        # Call the function directly instead of through a flow
        result = parse_tool_results.fn(result_path="/path/to/result.xml")
        
        # Assert the task failed as expected
        assert result.is_failed()
        assert "Failed to parse" in result.message


def test_analyze_remote_repo_fn():
    """Test the underlying function of analyze_remote_repo task directly."""
    # Mock the dependencies using object patching for resilience
    with patch.object(tool_repomix_module, 'run_repomix') as mock_run_repomix, \
         patch.object(tool_repomix_module, 'create_markdown_artifact') as mock_artifact:
        
        # Set up the mock to return a successful result
        mock_run_repomix.return_value = (0, "/path/to/output.xml", None)
        
        # Call the task function directly
        result = analyze_remote_repo.fn(
            remote_url="https://github.com/test/repo", 
            config_path="/path/to/config.json", 
            result_path="/path/to/result.xml"
        )
        
        # Assert the result is as expected
        assert hasattr(result, 'is_completed') and result.is_completed()
        assert result.data["repo_url"] == "https://github.com/test/repo"
        assert result.data["return_code"] == 0
        assert result.data["output_path"] == "/path/to/output.xml"
        assert result.data["stderr"] is None

if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 