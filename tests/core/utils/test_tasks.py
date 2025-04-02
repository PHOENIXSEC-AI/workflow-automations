"""
Tests for task-related utility functions.

This file tests the task utility functions that interact with
Prefect task context and provide helper functionality.
"""
import time
import pytest
from unittest.mock import patch, MagicMock

from core.utils.tasks import (
    create_task_batches,
    get_current_retry_count,
    get_current_task_run_id
)


def test_create_task_batches_even_division():
    """Test create_task_batches with items that divide evenly into batches."""
    items = [1, 2, 3, 4, 5, 6]
    batch_size = 2
    
    batches = create_task_batches(items, batch_size)
    
    assert len(batches) == 3
    assert batches[0] == [1, 2]
    assert batches[1] == [3, 4]
    assert batches[2] == [5, 6]


def test_create_task_batches_uneven_division():
    """Test create_task_batches with items that don't divide evenly into batches."""
    items = [1, 2, 3, 4, 5, 6, 7]
    batch_size = 3
    
    batches = create_task_batches(items, batch_size)
    
    assert len(batches) == 3
    assert batches[0] == [1, 2, 3]
    assert batches[1] == [4, 5, 6]
    assert batches[2] == [7]


def test_create_task_batches_empty_list():
    """Test create_task_batches with an empty list."""
    items = []
    batch_size = 5
    
    batches = create_task_batches(items, batch_size)
    
    assert len(batches) == 0
    assert batches == []


def test_create_task_batches_batch_size_larger_than_items():
    """Test create_task_batches with batch size larger than the list of items."""
    items = [1, 2, 3]
    batch_size = 5
    
    batches = create_task_batches(items, batch_size)
    
    assert len(batches) == 1
    assert batches[0] == [1, 2, 3]


def test_get_current_retry_count_success():
    """Test get_current_retry_count with a successful context retrieval."""
    # Create a mock context with run_count
    mock_context = MagicMock()
    mock_context.task_run.run_count = 3  # 3rd run means 2 retries
    
    with patch('core.utils.tasks.get_run_context', return_value=mock_context):
        retry_count = get_current_retry_count()
        
        assert retry_count == 2


def test_get_current_retry_count_failure():
    """Test get_current_retry_count with a context retrieval failure."""
    # Mock the get_run_context to raise an exception
    with patch('core.utils.tasks.get_run_context', side_effect=Exception("Context unavailable")):
        retry_count = get_current_retry_count()
        
        assert retry_count == 0  # Should default to 0 on exception


def test_get_current_task_run_id_success():
    """Test get_current_task_run_id with a successful context retrieval."""
    # Create a mock context with task run ID
    mock_context = MagicMock()
    mock_context.task_run.id = "test-task-id"
    
    with patch('core.utils.tasks.get_run_context', return_value=mock_context):
        task_id = get_current_task_run_id()
        
        assert task_id == "test-task-id"
        assert isinstance(task_id, str)


def test_get_current_task_run_id_failure():
    """Test get_current_task_run_id with a context retrieval failure."""
    # Mock get_run_context to raise an exception and mock time.time for predictable result
    with patch('core.utils.tasks.get_run_context', side_effect=Exception("Context unavailable")), \
         patch('core.utils.tasks.time.time', return_value=123456.789):
        
        task_id = get_current_task_run_id()
        
        assert task_id == "unknown-123456.789"
        assert isinstance(task_id, str)
        assert task_id.startswith("unknown-")


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 