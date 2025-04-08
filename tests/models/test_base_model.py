# tests/unit/models/test_base_models.py
import pytest
from workflows.agents.models import AgentAnalysisResult

class TestAgentAnalysisResult:
    def test_file_path_validation(self):
        """Test that file_path validation works correctly."""
        # Should raise ValueError when file_path is empty
        with pytest.raises(ValueError, match="file_path is required"):
            AgentAnalysisResult(file_path="").validate_file_path()
        
        # Should pass with valid file_path
        result = AgentAnalysisResult(file_path="test.py")
        assert result.validate_file_path() == result
    
    def test_default_factory(self):
        """Test the default factory method."""
        result = AgentAnalysisResult.default()
        assert result.file_path == 'default'
    
    def test_create_error_result(self):
        """Test the error result creation method."""
        error = "Test error"
        limitations = "Test limitations"
        
        result = AgentAnalysisResult.create_error_result(
            error_message=error,
            limitations=limitations,
            file_path="error.py"
        )
        
        assert result.file_path == "error.py"
        assert result.errors == error
        assert result.limitations == limitations
        
        # Test with default file_path
        result = AgentAnalysisResult.create_error_result(error_message=error)
        assert result.file_path == 'default'
        
        # Test when limitations is not provided
        result = AgentAnalysisResult.create_error_result(error_message=error)
        assert result.limitations == error
    
if __name__ == "__main__":
    pytest.main(["-xvs","--pdb", __file__])