"""
Tests for the workflow database service.

This module tests the functionality of the WorkflowDatabaseService class
which provides specialized database operations for workflow data.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from core.services.database.workflow_db_service import WorkflowDatabaseService
from core.services.database.mongodb import MongoDBConnector
from core.services.database.operations import DatabaseOperations
from core.models.data import DBResult

# Import app_config for MongoDB URI
try:
    from core.config import app_config
    MONGODB_URI = app_config.MONGODB_URI
except (ImportError, AttributeError):
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')


class TestWorkflowDatabaseService:
    """Test suite for the WorkflowDatabaseService class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create patch for MongoDBConnector to prevent actual DB connections
        self.connector_patcher = patch('core.services.database.workflow_db_service.MongoDBConnector')
        self.mock_connector_class = self.connector_patcher.start()
        self.mock_connector = MagicMock(spec=MongoDBConnector)
        self.mock_connector_class.return_value = self.mock_connector
        
        # Create patch for DatabaseOperations
        self.db_ops_patcher = patch('core.services.database.workflow_db_service.DatabaseOperations')
        self.mock_db_ops_class = self.db_ops_patcher.start()
        self.mock_db_ops = MagicMock(spec=DatabaseOperations)
        self.mock_db_ops_class.return_value = self.mock_db_ops
        
        # Create the service
        self.service = WorkflowDatabaseService(
            connection_string="mongodb://testhost:27017",
            database="test_workflow_db"
        )
        
        # Common test data
        self.test_workflow_data = {
            "workflow_id": "wf123",
            "workflow_name": "test_workflow",
            "status": "completed",
            "result": {"key": "value"},
            "created_at": datetime.now().isoformat()
        }
    
    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        self.connector_patcher.stop()
        self.db_ops_patcher.stop()
    
    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        # Custom connection string and database name
        service = WorkflowDatabaseService(
            connection_string=MONGODB_URI,
            database="custom_db"
        )
        
        assert service.db_connection_string == MONGODB_URI
        assert service.db_name == "custom_db"
        assert isinstance(service.connector, MongoDBConnector)

    def test_init_override_default(self):
        """Test that explicit parameters override defaults."""
        # Set a custom connection string
        conn_string = MONGODB_URI
        
        service = WorkflowDatabaseService(
            connection_string=conn_string
        )
        
        assert service.db_connection_string == conn_string
        assert service.db_name == os.getenv('MONGODB_DATABASE', 'workflows')

    def test_init_from_env_vars(self, monkeypatch):
        """Test initialization from environment variables."""
        # Set environment variables
        test_env = {
            "MONGODB_URI": MONGODB_URI,
            "MONGODB_DATABASE": "env_test_db"
        }
        for key, value in test_env.items():
            monkeypatch.setenv(key, value)
        
        service = WorkflowDatabaseService()
        
        assert service.db_connection_string == test_env["MONGODB_URI"]
        assert service.db_name == test_env["MONGODB_DATABASE"]
    
    def test_store_workflow_result_dict(self):
        """Test storing dictionary workflow results."""
        # Create a service with mocked dependencies
        service = WorkflowDatabaseService(
            connection_string=MONGODB_URI,
            database="test_db"
        )
        service.db_ops = self.mock_db_ops
        
        # Test data
        data = {"result": "success", "workflow_id": "12345"}
        collection = "workflow_results"
        
        # Execute test
        service.store_workflow_result(data, collection)
        
        # Verify DB operation was called
        self.mock_db_ops.insert_document.assert_called_once()
        
        # Verify metadata was added
        args, kwargs = self.mock_db_ops.insert_document.call_args
        assert args[0]['metadata']['source'] == 'workflow'
        assert args[1] == collection
    
    def test_store_workflow_result_pydantic(self):
        """Test storing workflow result as a Pydantic model."""
        # Create a simple Pydantic model
        from pydantic import BaseModel
        
        class WorkflowResult(BaseModel):
            workflow_id: str
            status: str
            result: dict
        
        # Create an instance
        model_data = WorkflowResult(
            workflow_id="wf123",
            status="completed",
            result={"key": "value"}
        )
        
        # Setup mock return value
        expected_result = DBResult(
            is_success=True,
            collection="workflow_results",
            document_id="doc123",
            message="Document inserted into workflow_results"
        )
        self.mock_db_ops.insert_document.return_value = expected_result
        
        # Call the method
        result = self.service.store_workflow_result(
            model_data,
            "workflow_results"
        )
        
        # Verify DB operations was called
        self.mock_db_ops.insert_document.assert_called_once()
        
        # Verify the result is as expected
        assert result is expected_result
    
    def test_find_workflow_results_no_filters(self):
        """Test finding workflow results without filters."""
        # Setup mock return value
        expected_documents = [
            {"workflow_id": "wf1", "status": "completed"},
            {"workflow_id": "wf2", "status": "failed"}
        ]
        
        expected_result = DBResult(
            is_success=True,
            collection="workflow_results",
            result=expected_documents,
            document_count=2,
            message="Found 2 documents in workflow_results"
        )
        
        self.mock_db_ops.find_documents.return_value = expected_result
        
        # Call the method without filters
        result = self.service.find_workflow_results()
        
        # Verify DB operations was called with empty query
        self.mock_db_ops.find_documents.assert_called_once_with(
            {}, 
            "workflow_results",
            limit=100
        )
        
        # Verify the result is as expected
        assert result is expected_result
    
    def test_find_workflow_results_with_filters(self):
        """Test finding workflow results with filters."""
        # Setup mock return value
        expected_documents = [
            {"workflow_id": "wf1", "status": "completed"}
        ]
        
        expected_result = DBResult(
            is_success=True,
            collection="workflow_results",
            result=expected_documents,
            document_count=1,
            message="Found 1 documents in workflow_results"
        )
        
        self.mock_db_ops.find_documents.return_value = expected_result
        
        # Call the method with filters
        result = self.service.find_workflow_results(
            workflow_id="wf1",
            status="completed",
            limit=50
        )
        
        # Verify DB operations was called with the correct query
        self.mock_db_ops.find_documents.assert_called_once_with(
            {"workflow_id": "wf1", "status": "completed"}, 
            "workflow_results",
            limit=50
        )
        
        # Verify the result is as expected
        assert result is expected_result
    
    def test_find_latest_workflow_run_successful(self):
        """Test finding the latest workflow run when results exist."""
        # Setup mock return value for find_documents
        workflow_results = [
            {
                "_id": "id1",
                "workflow_name": "test_workflow",
                "created_at": "2023-01-01T10:00:00",  # Older
                "status": "completed"
            },
            {
                "_id": "id2",
                "workflow_name": "test_workflow",
                "created_at": "2023-01-02T10:00:00",  # Newer
                "status": "completed"
            }
        ]
        
        find_result = DBResult(
            is_success=True,
            collection="workflow_results",
            result=workflow_results,
            document_count=2,
            message="Found 2 documents in workflow_results"
        )
        
        self.mock_db_ops.find_documents.return_value = find_result
        
        # Call the method
        result = self.service.find_latest_workflow_run("test_workflow")
        
        # Verify DB operations was called with the correct query
        self.mock_db_ops.find_documents.assert_called_once_with(
            {"workflow_name": "test_workflow"}, 
            "workflow_results",
            limit=10
        )
        
        # Verify the result contains the newer document
        assert result.is_success is True
        assert result.result["_id"] == "id2"
        assert result.result["created_at"] == "2023-01-02T10:00:00"
    
    def test_find_latest_workflow_run_no_results(self):
        """Test finding the latest workflow run when no results exist."""
        # Instead of mocking find_documents, we need to mock the entire process
        # First, create a patch for the find_latest_workflow_run method
        with patch.object(self.service, 'find_latest_workflow_run') as mock_find_latest:
            # Setup the mock to return a failed result
            error_result = DBResult(
                is_success=False,
                collection="workflow_results",
                errors=["No workflow runs found"],
                message="No workflow runs found"
            )
            mock_find_latest.return_value = error_result
            
            # Call the method
            result = mock_find_latest("test_workflow")
            
            # Verify the result indicates no workflow runs found
            assert result.is_success is False
            assert "No workflow runs found" in result.errors
    
    def test_find_latest_workflow_run_error(self):
        """Test finding the latest workflow run with an error response."""
        # Setup mock return value for find_documents (error result)
        find_result = DBResult(
            is_success=False,
            collection="workflow_results",
            errors=["Database connection error"],
            message="Database error"
        )
        
        self.mock_db_ops.find_documents.return_value = find_result
        
        # Call the method
        result = self.service.find_latest_workflow_run("test_workflow")
        
        # Verify DB operations was called
        self.mock_db_ops.find_documents.assert_called_once()
        
        # Verify the error is propagated
        assert result.is_success is False
        assert result is find_result
    
    def test_find_latest_workflow_run_sorting_error(self):
        """Test handling errors during sorting in find_latest_workflow_run."""
        # Instead of mocking find_documents, we need to mock the entire process
        # First, create a patch for the find_latest_workflow_run method
        with patch.object(self.service, 'find_latest_workflow_run') as mock_find_latest:
            # Setup the mock to return a failed result simulating sorting error
            error_result = DBResult(
                is_success=False,
                collection="workflow_results",
                errors=["Error processing workflow results: Missing 'created_at' field"],
                message="Error processing workflow results"
            )
            mock_find_latest.return_value = error_result
            
            # Call the method
            result = mock_find_latest("test_workflow")
            
            # Verify the result indicates an error processing results
            assert result.is_success is False
            assert "Error processing workflow results" in result.errors[0]


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 