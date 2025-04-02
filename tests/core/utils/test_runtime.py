"""
Tests for runtime utilities.

This file tests the runtime utility functions which retrieve
and format Prefect runtime context information.
"""
import pytest
from unittest.mock import patch, MagicMock

from core.utils.runtime import (
    get_runtime_task_id,
    get_ai_run_context,
    get_runtime_context,
    get_flow_name
)


# Helper function to create a standard mock runtime context
def create_mock_runtime():
    """Create a standard mock for Prefect runtime."""
    mock_runtime = MagicMock()
    
    # Set up flow run properties
    mock_runtime.flow_run = MagicMock()
    mock_runtime.flow_run.id = "test-flow-id"
    mock_runtime.flow_run.flow_name = "test-flow"
    mock_runtime.flow_run.name = "test-flow-run"
    mock_runtime.flow_run.run_count = 1
    
    # Set up task run properties
    mock_runtime.task_run = MagicMock()
    mock_runtime.task_run.id = "test-task-id"
    mock_runtime.task_run.name = "test-task"
    mock_runtime.task_run.parameters = {}
    
    return mock_runtime


def test_get_runtime_task_id_success():
    """Test get_runtime_task_id when task_run.id is available."""
    mock_runtime = create_mock_runtime()
    
    with patch('core.utils.runtime.runtime', mock_runtime):
        task_id = get_runtime_task_id()
        
        assert task_id == "test-task-id"
        assert isinstance(task_id, str)


def test_get_runtime_task_id_missing():
    """Test get_runtime_task_id when task_run.id is not available."""
    mock_runtime = create_mock_runtime()
    mock_runtime.task_run.id = None
    
    with patch('core.utils.runtime.runtime', mock_runtime):
        task_id = get_runtime_task_id()
        
        assert task_id == ""
        assert isinstance(task_id, str)


def test_get_ai_run_context_with_ctx():
    """Test get_ai_run_context when ctx parameter is available."""
    mock_runtime = create_mock_runtime()
    
    # Create a mock ctx object with a to_dict method
    mock_ctx = MagicMock()
    mock_ctx.to_dict.return_value = {
        "db_name": "test_db",
        "obj_id": "test_obj_id"
    }
    
    mock_runtime.task_run.parameters = {"ctx": mock_ctx}
    
    with patch('core.utils.runtime.runtime', mock_runtime):
        ctx_dict = get_ai_run_context()
        
        assert ctx_dict == {"db_name": "test_db", "obj_id": "test_obj_id"}
        assert isinstance(ctx_dict, dict)


def test_get_ai_run_context_no_ctx():
    """Test get_ai_run_context when ctx parameter is not available."""
    mock_runtime = create_mock_runtime()
    
    # Ensure parameters doesn't have ctx
    mock_runtime.task_run.parameters = {}
    
    with patch('core.utils.runtime.runtime', mock_runtime):
        ctx_dict = get_ai_run_context()
        
        assert ctx_dict == {}
        assert isinstance(ctx_dict, dict)


def test_get_runtime_context():
    """Test get_runtime_context returns the expected dictionary."""
    mock_runtime = create_mock_runtime()
    
    with patch('core.utils.runtime.runtime', mock_runtime), \
         patch('core.utils.runtime.get_runtime_task_id', return_value="test-task-id"):
        
        context = get_runtime_context()
        
        # Check all expected keys and values
        assert context["flow_id"] == "test-flow-id"
        assert context["flow_name"] == "test-flow"
        assert context["flow_run_name"] == "test-flow-run"
        assert context["flow_run_count"] == 1
        assert context["task_run_id"] == "test-task-id"
        assert context["task_run_name"] == "test-task"


def test_get_flow_name():
    """Test get_flow_name returns the expected format."""
    mock_runtime = create_mock_runtime()
    
    with patch('core.utils.runtime.runtime', mock_runtime):
        flow_name = get_flow_name()
        
        assert flow_name == "test-flow:test-flow-run"
        assert isinstance(flow_name, str)


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 