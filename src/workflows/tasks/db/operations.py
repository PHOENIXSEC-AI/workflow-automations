"""
Specialized database operations for workflows.
"""
import os
from typing import Dict, Union, Any, List, Optional

from prefect import task
from prefect.states import Completed, Failed
from prefect.artifacts import create_markdown_artifact

from pydantic import BaseModel

from core.utils.format.markdown_builder import generic_results_to_markdown
from core.utils import LoggerFactory

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

# Import app_config for MongoDB URI
try:
    from core.config import app_config
    DB_CONNECTION_STRING = app_config.MONGODB_URI
except (ImportError, AttributeError):
    DB_CONNECTION_STRING = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')

DB_NAME = os.getenv('MONGODB_DATABASE', 'workflows')

# Lazy-loaded database services
_db_service = None

def get_db_service():
    pass
    # """Get or initialize the workflow database service."""
    # global _db_service
    # if _db_service is None:
    #     logger.info(f"Creating Workflow DB Service")
    #     _db_service = WorkflowDatabaseService(
    #         connection_string=DB_CONNECTION_STRING,
    #         database=DB_NAME
    #     )
    # return _db_service

@task(name="store_results", retries=3, retry_delay_seconds=5)
def store_results(data: Union[BaseModel, Dict], coll_name: str):
    """
    Store data in MongoDB collection.
    
    Args:
        data: The data to store, either a Pydantic model or a dictionary
        coll_name: The collection name to store data in
        
    Returns:
        Prefect State: The result state of the operation
    """
    db_service = get_db_service()
    result = db_service.store_workflow_result(data, coll_name)
    
    # Create artifact with results
    markdown = generic_results_to_markdown(
        {
            "collection": result.collection,
            "result": result.result,
            "is_success": result.is_success,
            "errors": result.errors if result.errors else None
        }
    )
        
    create_markdown_artifact(
        markdown=markdown, 
        key=f"db-store-results-{coll_name}",
        description=f"MongoDB store operation for collection: {coll_name}"
    )
    
    if result.is_success:
        return Completed(data=result, message=f"✅ Successfully stored data in '{coll_name}'")
    else:
        return Failed(data=result, message=f"❌ Failed to store data in '{coll_name}'")

@task(name="retrieve_documents")
def retrieve_documents(query: Dict, coll_name: str, limit: int = 100):
    """
    Retrieve documents from MongoDB collection based on a query.
    
    Args:
        query: MongoDB query to filter documents
        coll_name: The collection name to query
        limit: Maximum number of documents to return (default: 100)
        
    Returns:
        Prefect State: The result state of the operation
    """
    db_service = get_db_service()
    result = db_service.db_ops.find_documents(query, coll_name, limit=limit)
    
    # Create artifact with result summary
    markdown = generic_results_to_markdown(
        {
            "collection": result.collection,
            "documents_count": result.document_count,
            "is_success": result.is_success,
            "errors": result.errors if result.errors else None
        }
    )
        
    create_markdown_artifact(
        markdown=markdown, 
        key=f"db-retrieve-documents-{coll_name}",
        description=f"MongoDB retrieve operation for collection: {coll_name}"
    )
    
    if result.is_success:
        return Completed(
            data=result, 
            message=f"✅ Retrieved {result.document_count} documents from '{coll_name}'"
        )
    else:
        return Failed(data=result, message=f"❌ Failed to retrieve documents from '{coll_name}'")
    
@task(name="retrieve_document_by_id")
def retrieve_document_by_id(doc_id: str, coll_name: str):
    """
    Retrieve a single document from MongoDB collection by its ID.
    
    Args:
        doc_id: The document ID to retrieve
        coll_name: The collection name to query
        
    Returns:
        Prefect State: The result state of the operation
    """
    db_service = get_db_service()
    result = db_service.db_ops.find_document_by_id(doc_id, coll_name)
    
    # Create artifact with result summary
    markdown = generic_results_to_markdown(
        {
            "collection": result.collection,
            "document_id": doc_id,
            "is_success": result.is_success,
            "errors": result.errors if result.errors else None
        }
    )
        
    create_markdown_artifact(
        markdown=markdown, 
        key=f"db-retrieve-document-{coll_name}-{doc_id[:8]}",
        description=f"MongoDB retrieve document operation for collection: {coll_name}"
    )
    
    if result.is_success:
        return Completed(
            data=result, 
            message=f"✅ Retrieved document with ID '{doc_id}' from '{coll_name}'"
        )
    else:
        return Failed(
            data=result, 
            message=f"❌ Failed to retrieve document with ID '{doc_id}' from '{coll_name}'"
        ) 