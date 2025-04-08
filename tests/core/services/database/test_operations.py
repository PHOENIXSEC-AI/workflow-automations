"""
Tests for database operations.

This module tests the functionality of the DatabaseOperations class
which provides common database operations across the application.
"""
import pytest
from unittest.mock import MagicMock, patch
from bson.objectid import ObjectId

from core.services.database.operations import DatabaseOperations
from core.services.database.mongodb import MongoDBConnector


class TestDatabaseOperations:
    """Test suite for the DatabaseOperations class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock for the MongoDB connector
        self.mock_connector = MagicMock(spec=MongoDBConnector)
        
        # Initialize the DatabaseOperations with the mock connector
        self.db_ops = DatabaseOperations(self.mock_connector)
        
        # Common test data
        self.test_collection = "test_collection"
        self.test_document = {"name": "Test Document", "value": 42}
        self.test_object_id = ObjectId()
        
        # Setup common mock return values
        self.mock_connector.insert_document.return_value = self.test_object_id
        
        # Add find_documents method to the mock - this was missing
        # In MongoDBConnector, find_documents would typically return a cursor
        # so we simulate that behavior by having it as an attribute of the mock
        self.mock_connector.find_documents = MagicMock()
    
    def test_insert_document_dict(self):
        """Test inserting a dictionary document."""
        # Call the method with a dictionary
        result = self.db_ops.insert_document(self.test_document, self.test_collection)
        
        # Verify connector method was called with correct parameters
        self.mock_connector.insert_document.assert_called_once_with(
            self.test_collection, 
            self.test_document
        )
        
        # Verify the result
        assert result.is_success is True
        assert result.document_id == str(self.test_object_id)
        assert result.collection == self.test_collection
    
    def test_insert_document_pydantic(self):
        """Test inserting a Pydantic model document."""
        # Create a simple Pydantic model
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        test_model = TestModel(name="Test Model", value=42)
        
        # Call the method with a Pydantic model
        result = self.db_ops.insert_document(test_model, self.test_collection)
        
        # Verify connector method was called with the model dictionary
        self.mock_connector.insert_document.assert_called_once()
        args, _ = self.mock_connector.insert_document.call_args
        assert args[0] == self.test_collection
        assert args[1]["name"] == "Test Model"
        assert args[1]["value"] == 42
        
        # Verify the result
        assert result.is_success is True
        assert result.document_id == str(self.test_object_id)
    
    def test_insert_document_no_data(self):
        """Test error when no data is provided."""
        result = self.db_ops.insert_document(None, self.test_collection)
        
        # Verify the connector was not called
        self.mock_connector.insert_document.assert_not_called()
        
        # Verify error result
        assert result.is_success is False
        assert "No data provided to store" in result.errors
    
    def test_insert_document_no_collection(self):
        """Test error when no collection is provided."""
        result = self.db_ops.insert_document(self.test_document, "")
        
        # Verify the connector was not called
        self.mock_connector.insert_document.assert_not_called()
        
        # Verify error result
        assert result.is_success is False
        assert "Collection name is required" in result.errors
    
    def test_insert_document_database_error(self):
        """Test handling database errors during insert."""
        # Setup the mock to raise an exception
        self.mock_connector.insert_document.side_effect = Exception("Database connection error")
        
        # Call the method
        result = self.db_ops.insert_document(self.test_document, self.test_collection)
        
        # Verify error result
        assert result.is_success is False
        assert "Database error: Database connection error" in result.errors
    
    def test_find_document(self):
        """Test finding a document."""
        # Setup the mock return value
        found_document = {"_id": self.test_object_id, **self.test_document}
        self.mock_connector.find_document.return_value = found_document
        
        # Call the method
        query = {"name": "Test Document"}
        result = self.db_ops.find_document(query, self.test_collection)
        
        # Verify connector method was called correctly
        self.mock_connector.find_document.assert_called_once_with(
            self.test_collection, 
            query
        )
        
        # Verify the result
        assert result.is_success is True
        assert result.result == found_document
        assert "Document found" in result.message
    
    def test_find_document_not_found(self):
        """Test when a document is not found."""
        # Setup the mock to return None (not found)
        self.mock_connector.find_document.return_value = None
        
        # Call the method
        query = {"name": "Non-existent Document"}
        result = self.db_ops.find_document(query, self.test_collection)
        
        # Verify error result
        assert result.is_success is False
        assert "Document not found" in result.errors
    
    def test_find_document_no_collection(self):
        """Test error when no collection is provided."""
        query = {"name": "Test Document"}
        result = self.db_ops.find_document(query, "")
        
        # Verify the connector was not called
        self.mock_connector.find_document.assert_not_called()
        
        # Verify error result
        assert result.is_success is False
        assert "Collection name is required" in result.errors
    
    def test_find_document_database_error(self):
        """Test handling database errors during find."""
        # Setup the mock to raise an exception
        self.mock_connector.find_document.side_effect = Exception("Database query error")
        
        # Call the method
        query = {"name": "Test Document"}
        result = self.db_ops.find_document(query, self.test_collection)
        
        # Verify error result
        assert result.is_success is False
        assert "Database error: Database query error" in result.errors
    
    def test_find_documents(self):
        """Test finding multiple documents."""
        # Setup the mock return value
        found_documents = [
            {"_id": ObjectId(), "name": "Doc 1", "value": 1},
            {"_id": ObjectId(), "name": "Doc 2", "value": 2}
        ]
        self.mock_connector.find_documents.return_value = found_documents
        
        # Call the method
        query = {"value": {"$gt": 0}}
        result = self.db_ops.find_documents(query, self.test_collection, limit=10)
        
        # Verify connector method was called correctly
        self.mock_connector.find_documents.assert_called_once_with(
            self.test_collection, 
            query,
            limit=10
        )
        
        # Verify the result
        assert result.is_success is True
        assert result.result == found_documents
        assert result.document_count == 2
        assert "Found 2 documents" in result.message
    
    def test_find_documents_no_collection(self):
        """Test error when no collection is provided for find_documents."""
        query = {"value": {"$gt": 0}}
        result = self.db_ops.find_documents(query, "")
        
        # Verify the connector was not called
        self.mock_connector.find_documents.assert_not_called()
        
        # Verify error result
        assert result.is_success is False
        assert "Collection name is required" in result.errors
    
    def test_find_documents_database_error(self):
        """Test handling database errors during find_documents."""
        # Setup the mock to raise an exception
        self.mock_connector.find_documents.side_effect = Exception("Database query error")
        
        # Call the method
        query = {"value": {"$gt": 0}}
        result = self.db_ops.find_documents(query, self.test_collection)
        
        # Verify error result
        assert result.is_success is False
        assert "Database error: Database query error" in result.errors
    
    def test_find_document_by_id_valid(self):
        """Test finding a document by a valid ID."""
        # Setup the mock for find_document
        found_document = {"_id": self.test_object_id, **self.test_document}
        self.mock_connector.find_document.return_value = found_document
        
        # Call the method
        result = self.db_ops.find_document_by_id(str(self.test_object_id), self.test_collection)
        
        # Verify connector method was called correctly
        self.mock_connector.find_document.assert_called_once_with(
            self.test_collection,
            {"_id": self.test_object_id}
        )
        
        # Verify the result
        assert result.is_success is True
        assert result.result == found_document
    
    def test_find_document_by_id_invalid(self):
        """Test error when an invalid ID is provided."""
        # Call the method with an invalid ObjectId
        result = self.db_ops.find_document_by_id("invalid-id", self.test_collection)
        
        # Verify the connector was not called
        self.mock_connector.find_document.assert_not_called()
        
        # Verify error result
        assert result.is_success is False
        assert "Invalid document ID or error" in result.errors[0]


if __name__ == "__main__":
    # Run all tests even if some fail
    pytest.main(["-vs", "--tb=short", "--no-header", "--continue-on-collection-errors", __file__]) 