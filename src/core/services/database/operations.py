"""
Common database operations for application services.
"""
from typing import Any, Dict, List, Optional, Union, Tuple
from pydantic import BaseModel

from core.utils.logger import LoggerFactory
from core.models.data import DBResult
from .mongodb import MongoDBConnector

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

class DatabaseOperations:
    """
    Common database operations used across the application.
    """
    
    def __init__(self, connector: MongoDBConnector):
        """
        Initialize with a database connector.
        
        Args:
            connector: An initialized MongoDB connector
        """
        self.connector = connector
    
    def insert_document(self, data: Union[BaseModel, Dict], collection: str) -> DBResult:
        """
        Insert a document into a collection.
        
        Args:
            data: The document data to insert (Pydantic model or dict)
            collection: The collection name
            
        Returns:
            DBResult with the operation result
        """
        result = DBResult(collection=collection)
        
        try:
            # Validate input data
            if not data:
                return result.add_error("No data provided to store")
            
            if not collection:
                return result.add_error("Collection name is required")
                
            # Convert to dictionary if it's a Pydantic model
            if hasattr(data, 'model_dump'):
                document = data.model_dump()
            elif isinstance(data, dict):
                document = data
            else:
                return result.add_error(f"Expected dict or Pydantic model, got {type(data)}")
            
            # Insert document
            doc_id = self.connector.insert_document(collection, document)
            
            # Return successful result
            return result.set_result(str(doc_id), f"Document inserted into {collection}").set_document_id(str(doc_id))
            
        except Exception as e:
            logger.error(f"Failed to insert document: {str(e)}")
            return result.add_error(f"Database error: {str(e)}")
    
    def find_document(self, query: Dict, collection: str) -> DBResult:
        """
        Find a single document in a collection.
        
        Args:
            query: Query to find the document
            collection: The collection name
            
        Returns:
            DBResult with the found document or error
        """
        result = DBResult(collection=collection)
        
        try:
            if not collection:
                return result.add_error("Collection name is required")
                
            document = self.connector.find_document(collection, query)
            
            if document:
                return result.set_result(document, f"Document found in {collection}")
            else:
                return result.add_error("Document not found")
                
        except Exception as e:
            logger.error(f"Failed to find document: {str(e)}")
            return result.add_error(f"Database error: {str(e)}")
    
    def find_documents(self, query: Dict, collection: str, limit: int = 100) -> DBResult:
        """
        Find multiple documents in a collection.
        
        Args:
            query: Query to find documents
            collection: The collection name
            limit: Maximum number of documents to return
            
        Returns:
            DBResult with found documents
        """
        result = DBResult(collection=collection)
        
        try:
            if not collection:
                return result.add_error("Collection name is required")
                
            # MongoDB's find() returns a cursor, so we convert to list
            documents = list(self.connector.find_documents(collection, query, limit=limit))
            
            result.set_document_count(len(documents))
            return result.set_result(documents, f"Found {len(documents)} documents in {collection}")
                
        except Exception as e:
            logger.error(f"Failed to find documents: {str(e)}")
            return result.add_error(f"Database error: {str(e)}")
            
    def find_document_by_id(self, doc_id: str, collection: str) -> DBResult:
        """
        Find a document by its ID.
        
        Args:
            doc_id: Document ID to find
            collection: The collection name
            
        Returns:
            DBResult with the found document
        """
        from bson.objectid import ObjectId
        
        try:
            # Check if the ID is a valid ObjectId
            object_id = ObjectId(doc_id)
            return self.find_document({"_id": object_id}, collection)
        except Exception as e:
            result = DBResult(collection=collection)
            return result.add_error(f"Invalid document ID or error: {str(e)}") 