"""
Tests for the create_agent_tasks function.

This module tests the create_agent_tasks function which creates
a list of agent tasks from repository context with content retrieval.
"""
import pytest
from unittest.mock import patch, MagicMock

from pydantic import BaseModel, Field

from workflows.tasks.ai_ops.utils import create_agent_tasks
from workflows.agents.models import AgentTask

# Create a test result model
class TestResultModel(BaseModel):
    """Test model for result validation"""
    file_path: str = Field(description="Path of the file")
    findings: list = Field(default_factory=list, description="List of findings")
    issues: list = Field(default_factory=list, description="List of issues")


class TestCreateAgentTasks:
    """Test suite for the create_agent_tasks function."""
    
    @pytest.fixture
    def test_repo_context(self):
        """Create a test repository context."""
        return {
            "obj_id": "test123",
            "repository_name": "test_repo",
            "db_name": "test_db",
            "files": [
                {
                    "path": "file1.py",
                    "content": "def test_function():\n    return True",
                    "content_token_count": 10
                },
                {
                    "path": "file2.py",
                    "content_reference": "GRIDFS:67ea73aec7f858517ef5865c",
                    "content_stored_separately": True,
                    "content_token_count": 100
                },
                {
                    "path": "file3.py",
                    "content_id": "30e71e76-504d-4f2a-b29b-3e0e9888987c",
                    "content_stored_separately": True,
                    "content_token_count": 150
                }
            ]
        }
    
    @pytest.fixture
    def instructions_template(self):
        """Create a test instructions template."""
        return """
        Please analyze the following file:
        
        File Path: {file_path}
        
        Content:
        ```
        {content}
        ```
        
        Return your findings in the following JSON format:
        {json_schema}
        """
    
    @pytest.fixture
    def mock_get_file_content(self):
        """Create a mock for get_file_content function."""
        with patch('workflows.tasks.ai_ops.utils.get_file_content') as mock:
            yield mock
    
    def test_create_agent_tasks_success(self, test_repo_context, instructions_template, mock_get_file_content):
        """Test successful creation of agent tasks."""
        # Mock the get_file_content function to return file content
        mock_get_file_content.side_effect = [
            ("def test_function():\n    return True", True),  # file1.py (direct content)
            ("def another_function():\n    return False", True),  # file2.py (via GridFS)
            ("class TestClass:\n    pass", True)  # file3.py (via content_id)
        ]
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=test_repo_context,
            result_type=TestResultModel
        )
        
        # Verify results
        assert len(tasks) == 3
        
        # Check that all tasks are of the correct type
        for task in tasks:
            assert isinstance(task, AgentTask)
            assert task.obj_id == "test123"
            assert task.repo_name == "test_repo"
        
        # Check file paths
        assert tasks[0].file_path == "file1.py"
        assert tasks[1].file_path == "file2.py"
        assert tasks[2].file_path == "file3.py"
        
        # Verify that get_file_content was called with correct arguments
        assert mock_get_file_content.call_count == 3
        mock_get_file_content.assert_any_call(test_repo_context["files"][0], "test_db")
        mock_get_file_content.assert_any_call(test_repo_context["files"][1], "test_db")
        mock_get_file_content.assert_any_call(test_repo_context["files"][2], "test_db")
    
    def test_create_agent_tasks_with_failures(self, test_repo_context, instructions_template, mock_get_file_content):
        """Test creating agent tasks when some content retrievals fail."""
        # Mock the get_file_content function to return some failures
        mock_get_file_content.side_effect = [
            ("def test_function():\n    return True", True),  # file1.py (direct content)
            (None, False),  # file2.py (content retrieval failed)
            ("class TestClass:\n    pass", True)  # file3.py (via content_id)
        ]
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=test_repo_context,
            result_type=TestResultModel
        )
        
        # Verify results - should only have 2 tasks
        assert len(tasks) == 2
        
        # Check file paths
        assert tasks[0].file_path == "file1.py"
        assert tasks[1].file_path == "file3.py"
        
        # Verify that get_file_content was called with correct arguments
        assert mock_get_file_content.call_count == 3
    
    def test_create_agent_tasks_missing_file_path(self, test_repo_context, instructions_template, mock_get_file_content):
        """Test handling files with missing path."""
        # Add a file without a path
        test_repo_context["files"].append({"content": "# Missing path file"})
        
        # Mock the get_file_content function
        mock_get_file_content.side_effect = [
            ("def test_function():\n    return True", True),
            ("def another_function():\n    return False", True),
            ("class TestClass:\n    pass", True)
        ]
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=test_repo_context,
            result_type=TestResultModel
        )
        
        # Verify results - should only have 3 tasks (skipped the one without path)
        assert len(tasks) == 3
        
        # Verify that get_file_content was called with correct arguments
        assert mock_get_file_content.call_count == 3
    
    def test_create_agent_tasks_empty_files(self, instructions_template, mock_get_file_content):
        """Test handling of empty files list."""
        # Create a repo context with no files
        repo_context = {
            "obj_id": "test123",
            "repository_name": "test_repo",
            "db_name": "test_db",
            "files": []  # Empty files list
        }
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=repo_context,
            result_type=TestResultModel
        )
        
        # Verify results
        assert len(tasks) == 0
        
        # Verify that get_file_content was not called
        mock_get_file_content.assert_not_called()
    
    def test_create_agent_tasks_missing_files_key(self, instructions_template, mock_get_file_content):
        """Test handling of missing files key."""
        # Create a repo context without a files key
        repo_context = {
            "obj_id": "test123",
            "repository_name": "test_repo",
            "db_name": "test_db"
            # No 'files' key
        }
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=repo_context,
            result_type=TestResultModel
        )
        
        # Verify results
        assert len(tasks) == 0
        
        # Verify that get_file_content was not called
        mock_get_file_content.assert_not_called()
    
    def test_create_agent_tasks_exception_handling(self, test_repo_context, instructions_template, mock_get_file_content):
        """Test handling of exceptions during processing."""
        # Mock get_file_content to raise an exception
        mock_get_file_content.side_effect = Exception("Test error")
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=test_repo_context,
            result_type=TestResultModel
        )
        
        # Verify results - should have 0 tasks due to exceptions
        assert len(tasks) == 0
        
        # Verify that get_file_content was called
        assert mock_get_file_content.call_count > 0
    
    def test_create_agent_tasks_db_name_fallback(self, instructions_template, mock_get_file_content):
        """Test fallback to app_config.MONGODB_DATABASE when db_name is missing."""
        # Create a repo context without db_name
        repo_context = {
            "obj_id": "test123",
            "repository_name": "test_repo",
            "files": [
                {
                    "path": "file1.py",
                    "content": "def test_function():\n    return True"
                }
            ]
        }
        
        # Mock get_file_content to return success
        mock_get_file_content.return_value = ("def test_function():\n    return True", True)
        
        # Mock app_config
        with patch('workflows.tasks.ai_ops.utils.app_config') as mock_config:
            mock_config.MONGODB_DATABASE = "default_db"
            
            # Call the function
            tasks = create_agent_tasks(
                instructions=instructions_template,
                repo_context=repo_context,
                result_type=TestResultModel
            )
            
            # Verify results
            assert len(tasks) == 1
            
            # Verify that get_file_content was called with the default db name
            mock_get_file_content.assert_called_with(repo_context["files"][0], "default_db")
    
    def test_create_agent_tasks_instruction_formatting(self, test_repo_context, mock_get_file_content):
        """Test that instructions are properly formatted with placeholders."""
        # Simple instructions template with placeholders
        instructions_template = "Path: {file_path}, Content: {content}, Schema: {json_schema}"
        
        # Mock get_file_content to return success
        mock_get_file_content.return_value = ("test content", True)
        
        # Call the function
        tasks = create_agent_tasks(
            instructions=instructions_template,
            repo_context=test_repo_context,
            result_type=TestResultModel
        )
        
        # Verify results
        assert len(tasks) == 3
        
        # Check the formatted instructions
        for task in tasks:
            assert "Path: " + task.file_path in task.instructions
            assert "Content: test content" in task.instructions
            assert "Schema: " in task.instructions
            assert "TestResultModel" in task.instructions
            
if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", __file__]) 