import pytest
from datetime import datetime
from workflows.agents.models import (
    AgentTask, 
    TokenUsage, 
    AgentSuccessResult, 
    AgentAnalysisResult,
    AgentErrorResult
)

class TestAgentTask:
    def test_creation(self):
        """Test that AgentTask can be created with required fields."""
        task = AgentTask(
            instructions="Test instructions",
            obj_id="test_obj_id",
            repo_name="test_repo",
            file_path="test/path.py"
        )
        
        assert task.instructions == "Test instructions"
        assert task.obj_id == "test_obj_id"
        assert task.repo_name == "test_repo"
        assert task.file_path == "test/path.py"
    
    def test_minimal_creation(self):
        """Test that AgentTask can be created with only required fields."""
        task = AgentTask(instructions="Test instructions")
        
        assert task.instructions == "Test instructions"
        assert task.obj_id == ""
        assert task.repo_name == ""
        assert task.file_path is None

class TestTokenUsage:
    def test_creation(self):
        """Test that TokenUsage can be created with all fields."""
        usage = TokenUsage(
            prompt=100,
            completion=50,
            total=150
        )
        
        assert usage.prompt == 100
        assert usage.completion == 50
        assert usage.total == 150
    
    def test_default_values(self):
        """Test that default values are applied correctly."""
        usage = TokenUsage()
        
        assert usage.prompt is None
        assert usage.completion is None
        assert usage.total is None

class TestAgentSuccessResult:
    def test_creation_with_string_result(self):
        """Test creating an AgentSuccessResult with a string result."""
        task = AgentTask(instructions="Test instructions")
        result = AgentSuccessResult(
            task=task,
            result="Test result string",
            duration_seconds=1.5,
            agent="test-agent"
        )
        
        assert result.task == task
        assert result.is_success is True
        assert result.result == "Test result string"
        assert result.duration_seconds == 1.5
        assert result.agent == "test-agent"
        assert result.model is None
        assert result.tokens is None
        assert result.prompt_index is None
        assert isinstance(result.timestamp, datetime)
    
    def test_creation_with_analysis_result(self):
        """Test creating an AgentSuccessResult with an AgentAnalysisResult."""
        task = AgentTask(instructions="Test instructions")
        analysis_result = AgentAnalysisResult(file_path="test.py")
        
        result = AgentSuccessResult(
            task=task,
            result=analysis_result,
            duration_seconds=1.5,
            agent="test-agent",
            model="gpt-4",
            tokens=TokenUsage(prompt=100, completion=50, total=150),
            prompt_index=0
        )
        
        assert result.task == task
        assert result.is_success is True
        assert result.result == analysis_result
        assert result.duration_seconds == 1.5
        assert result.agent == "test-agent"
        assert result.model == "gpt-4"
        assert result.tokens.prompt == 100
        assert result.tokens.completion == 50
        assert result.tokens.total == 150
        assert result.prompt_index == 0

class TestAgentErrorResult:
    def test_creation(self):
        """Test creating an AgentErrorResult."""
        task = AgentTask(instructions="Test instructions")
        error = AgentErrorResult(
            task=task,
            error_type="API_ERROR",
            message="Test error message",
            duration_seconds=0.5,
            agent="test-agent",
            status_code=500,
            exception_type="RuntimeError"
        )
        
        assert error.task == task
        assert error.is_success is False
        assert error.error_type == "API_ERROR"
        assert error.message == "Test error message"
        assert error.status_code == 500
        assert error.exception_type == "RuntimeError"
        assert isinstance(error.timestamp, datetime)
    
    def test_minimal_creation(self):
        """Test creating an AgentErrorResult with only required fields."""
        task = AgentTask(instructions="Test instructions")
        error = AgentErrorResult(
            task=task,
            error_type="VALIDATION_ERROR",
            message="Required field missing"
        )
        
        assert error.task == task
        assert error.is_success is False
        assert error.error_type == "VALIDATION_ERROR"
        assert error.message == "Required field missing"
        assert error.status_code is None
        assert error.exception_type is None
        assert error.prompt_index is None

if __name__ == "__main__":
    pytest.main(["-xvs", "--pdb", __file__]) 