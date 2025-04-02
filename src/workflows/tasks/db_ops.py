import os
from typing import Any, Dict, List, Optional, Union
from bson.objectid import ObjectId

from pydantic import BaseModel, ValidationError

from prefect import task
from prefect.states import Completed, Failed
from prefect.artifacts import create_markdown_artifact

from core.utils import LoggerFactory
from core.utils.format import generic_results_to_markdown
from core.services import MongoDBConnector

from workflows.agents.models import AgentAnalysisResult

from core.config import app_config
logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

# Get connection details from environment variables for security
DB_CONNECTION_STRING = os.getenv('MONGODB_URI',None)
DB_NAME = os.getenv('MONGODB_DATABASE', 'workflows')

# Lazy-loaded database client to improve startup performance
_db_client = None

def get_db_client():
    """Get or initialize the database client."""
    global _db_client
    if _db_client is None:
        logger.info(f"Creating DB Connector")
        _db_client = MongoDBConnector(
            database=DB_NAME,
            connection_string=DB_CONNECTION_STRING
        )
    return _db_client


class DBTaskResult(BaseModel):
    """Result of a database operation task.
    
    This class provides methods for dynamically adding fields to the model.
    """
    db_result: Any
    is_success: bool = False
    errors: Optional[List[str]] = []
    collection: str = ""


@task(name="store_results", retries=3, retry_delay_seconds=5)
def store_results(data: Union[BaseModel, Dict], coll_name: str) -> DBTaskResult:
    """
    Store data in MongoDB collection.
    
    Args:
        data: The data to store, either a Pydantic model or a dictionary
        coll_name: The collection name to store data in
        
    Returns:
        DBTaskResult: The result of the database operation
    
    Raises:
        Exception: Any exceptions that occur during the operation are caught,
                logged, and returned as part of the result
    """
    task_result = None
    
    try:
        # Validate input data
        if not data:
            raise ValueError("No data provided to store")
        
        if not coll_name:
            raise ValueError("Collection name is required")
            
        # Convert to dictionary if it's a Pydantic model
        if hasattr(data, 'model_dump'):
            document = data.model_dump()
        elif isinstance(data, dict):
            document = data
        else:
            raise TypeError(f"Expected dict or Pydantic model, got {type(data)}")
        
        # Get DB client and insert document
        db_client = get_db_client()
        doc_id = db_client.insert_document(coll_name, document)
        
        task_result = DBTaskResult(
            db_result=str(doc_id),
            is_success=True,
            collection=coll_name
        )
        
    except ValidationError as e:
        err_msg = f"Data validation error: {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(db_result=None, is_success=False, errors=[err_msg], collection=coll_name)
    except Exception as e:
        err_msg = f"Failed to store data in collection '{coll_name}': {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(db_result=None, is_success=False, errors=[err_msg], collection=coll_name)
    finally:
        if task_result and task_result.is_success:
            state = Completed(data=task_result, message=f"✅ Successfully stored data in '{coll_name}'")
        else:
            state = Failed(data=task_result, message=f"❌ Failed to store data in '{coll_name}'")
        
        # Create artifact with results
        t_r_markdown = generic_results_to_markdown(
            {
                "collection": task_result.collection,
                "result": task_result.db_result,
                "is_success": task_result.is_success,
                "errors": task_result.errors if task_result.errors else None
            }
        )
            
        create_markdown_artifact(
            markdown=t_r_markdown, 
            key=f"db-store-results-{coll_name}",
            description=f"MongoDB store operation for collection: {coll_name}"
        )
        
        return state


@task(name="retrieve_documents")
def retrieve_documents(query: Dict, coll_name: str, limit: int = 100) -> DBTaskResult:
    """
    Retrieve documents from MongoDB collection based on a query.
    
    Args:
        query: MongoDB query to filter documents
        coll_name: The collection name to query
        limit: Maximum number of documents to return (default: 100)
        
    Returns:
        DBTaskResult: The result of the database operation
    """
    task_result = None
    
    try:
        if not coll_name:
            raise ValueError("Collection name is required")
            
        db_client = get_db_client()
        documents = list(db_client.find_documents(coll_name, query, limit=limit))
        
        task_result = DBTaskResult(
            db_result=documents,
            is_success=True,
            collection=coll_name
        )
        
    except Exception as e:
        err_msg = f"Failed to retrieve documents from '{coll_name}': {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(db_result=None, is_success=False, errors=[err_msg], collection=coll_name)
    finally:
        if task_result and task_result.is_success:
            state = Completed(
                data=task_result, 
                message=f"✅ Retrieved {len(task_result.db_result)} documents from '{coll_name}'"
            )
        else:
            state = Failed(data=task_result, message=f"❌ Failed to retrieve documents from '{coll_name}'")
        
        # Create artifact with result summary
        t_r_markdown = generic_results_to_markdown(
            {
                "collection": task_result.collection,
                "documents_count": len(task_result.db_result) if task_result.is_success else 0,
                "is_success": task_result.is_success,
                "errors": task_result.errors if task_result.errors else None
            }
        )
            
        create_markdown_artifact(
            markdown=t_r_markdown, 
            key=f"db-retrieve-documents-{coll_name}",
            description=f"MongoDB retrieve operation for collection: {coll_name}"
        )
        
        return state
    
@task(name="retrieve_document_by_id")
async def db_retrieve_document_by_id(doc_id: str, coll_name: str, db_name: Optional[str] = None, create_artifact:bool=True) -> DBTaskResult:
    """
    Retrieve a single document from MongoDB collection by its ID.
    
    Args:
        doc_id: The document ID to retrieve (can be string or ObjectId compatible)
        coll_name: The collection name to query
        db_name: Optional database name override
        
    Returns:
        DBTaskResult: The result of the database operation containing the document
    """
    task_result = None
    actual_db_name = db_name or DB_NAME
    
    try:
        if not coll_name:
            raise ValueError("Collection name is required")
        
        if not doc_id:
            raise ValueError("Document ID is required")
            
        db_client = get_db_client()
        
        # Try to convert to ObjectId if it looks like a MongoDB ID
        mongo_id = None
        if len(doc_id) == 24 and all(c in '0123456789abcdef' for c in doc_id.lower()):
            try:
                mongo_id = ObjectId(doc_id)
            except Exception:
                # Not a valid ObjectId, will use as string
                pass
        
        # Access the collection directly
        collection = db_client.client[actual_db_name][coll_name]
        
        # First try with ObjectId if available
        document = None
        if mongo_id:
            document = collection.find_one({"_id": mongo_id})
            
        # If not found, try with string ID
        if not document:
            document = collection.find_one({"_id": doc_id})
            
        # If still not found, try common ID field names
        if not document:
            for field in ["id", "file_id", "fileId", "documentId"]:
                document = collection.find_one({field: doc_id})
                if document:
                    break
        
        if document:
            task_result = DBTaskResult(
                db_result=document,
                is_success=True,
                collection=coll_name
            )
        else:
            err_msg = f"No document found with ID '{doc_id}' in collection '{coll_name}'"
            logger.warning(err_msg)
            task_result = DBTaskResult(
                db_result=None, 
                is_success=False, 
                errors=[err_msg], 
                collection=coll_name
            )
        
    except Exception as e:
        err_msg = f"Failed to retrieve document with ID '{doc_id}' from '{coll_name}': {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(
            db_result=None, 
            is_success=False, 
            errors=[err_msg], 
            collection=coll_name
        )
    finally:
        if task_result and task_result.is_success:
            state = Completed(
                data=task_result, 
                message=f"✅ Retrieved document with ID '{doc_id}' from '{coll_name}'"
            )
        else:
            state = Failed(
                data=task_result, 
                message=f"❌ Failed to retrieve document with ID '{doc_id}' from '{coll_name}'"
            )
        
        if create_artifact:
            # Create artifact with result summary
            t_r_markdown = generic_results_to_markdown(
                {
                    "collection": task_result.collection,
                    "document_id": doc_id,
                    "document_found": task_result.is_success,
                    "is_success": task_result.is_success,
                    "errors": task_result.errors if task_result.errors else None
                }
            )
                
            await create_markdown_artifact(
                markdown=t_r_markdown, 
                key=f"db-retrieve-document-{coll_name}-{doc_id[:8]}",
                description=f"MongoDB retrieve document operation for collection: {coll_name}"
            )
        
        return state


@task(name="db_merge_documents_aggregation")
async def db_merge_documents_aggregation(
    doc_id: str, 
    enrichment_data: Dict[str, Any], 
    coll_name: str, 
    db_name: Optional[str] = None,
    array_field: Optional[str] = None,
    array_path_field: Optional[str] = "path"
) -> DBTaskResult:
    """
    Merge enrichment data into an existing document using MongoDB's aggregation pipeline.
    
    This task demonstrates how to use MongoDB aggregation pipeline to enrich documents with
    analysis results, especially when those results need to be merged into specific array elements.
    
    Args:
        doc_id: The document ID to enrich (can be string or ObjectId compatible)
        enrichment_data: Dictionary of data to merge into the document
        coll_name: The collection name where the document is stored
        db_name: Optional database name override
        array_field: Optional name of array field (e.g. 'files') for array element updates
        array_path_field: Field name used for matching array elements (default: 'path')
        
    Returns:
        DBTaskResult: The result of the merge operation containing the updated document
    """
    task_result = None
    actual_db_name = db_name or DB_NAME
    
    try:
        if not coll_name:
            raise ValueError("Collection name is required")
        
        if not doc_id:
            raise ValueError("Document ID is required")
            
        if not enrichment_data:
            raise ValueError("Enrichment data is required")
        
        db_client = get_db_client()
        
        # Try to convert to ObjectId if it looks like a MongoDB ID
        mongo_id = None
        if len(doc_id) == 24:
            try:
                mongo_id = ObjectId(doc_id)
            except Exception:
                # Not a valid ObjectId, will use as string
                pass
        
        # Access the collection directly for more advanced operations
        collection = db_client.client[actual_db_name][coll_name]
        
        # Prepare query to find the document
        doc_query = {"_id": mongo_id if mongo_id else doc_id}
        
        # First check if document exists
        existing_doc = collection.find_one(doc_query)
        
        if not existing_doc:
            raise ValueError(f"Document with ID '{doc_id}' not found in collection '{coll_name}'")
        
        # Initialize aggregation pipeline
        pipeline = []
        
        # Start with matching the document by ID
        pipeline.append({"$match": doc_query})
        
        # Process array-specific updates
        array_update_stage = None
        if array_field and array_field in existing_doc:
            # Extract array-specific enrichments
            array_updates = {}
            
            # Get all paths from this array field in the existing document
            existing_paths = {item.get(array_path_field): idx 
                            for idx, item in enumerate(existing_doc[array_field])
                            if array_path_field in item}
            
            # For each file path in our enrichment data, create direct updates
            for file_path, file_idx in existing_paths.items():
                # Skip if we don't have this path in our data
                if file_path not in enrichment_data:
                    continue
                    
                # Found a matching path, prepare updates for this element
                if file_path not in array_updates:
                    array_updates[file_path] = {}
                
                # Add all the enrichment data for this path
                # file_path maps directly to path in the array items
                array_updates[file_path] = enrichment_data[file_path]
            
            # If we have array updates, create an update stage
            if array_updates:
                # Define case expressions for each path
                case_expressions = []
                for path, updates in array_updates.items():
                    case_expressions.append({
                        "case": {"$eq": [f"$$element.{array_path_field}", path]},
                        "then": {
                            "$mergeObjects": [
                                "$$element",
                                {
                                    "$mergeObjects": [
                                        {"$ifNull": ["$$element.enrichment", {}]},
                                        updates
                                    ]
                                }
                            ]
                        }
                    })
                
                # Add a default case to handle elements that don't match any path
                case_expressions.append({
                    "case": True,
                    "then": "$$element"
                })
                
                # Create the array update stage using $map
                array_update_stage = {
                    "$addFields": {
                        array_field: {
                            "$map": {
                                "input": f"${array_field}",
                                "as": "element",
                                "in": {
                                    "$switch": {
                                        "branches": case_expressions
                                    }
                                }
                            }
                        }
                    }
                }
                
                pipeline.append(array_update_stage)
        
        # If we have a pipeline with updates, execute it and update the document
        if len(pipeline) > 1:  # More than just the $match stage
            # Add a $merge stage to update the document in-place
            pipeline.append({
                "$merge": {
                    "into": coll_name,
                    "on": "_id",
                    "whenMatched": "replace",
                    "whenNotMatched": "discard"
                }
            })
            
            # Execute the pipeline
            db_client.aggregate(coll_name, pipeline)
            
            # Retrieve the updated document to return
            updated_doc = collection.find_one(doc_query)
            
            task_result = DBTaskResult(
                db_result=updated_doc,
                is_success=True,
                collection=coll_name
            )
        else:
            # No actual updates were added to the pipeline
            err_msg = f"No update operations generated for document '{doc_id}'"
            logger.warning(err_msg)
            task_result = DBTaskResult(
                db_result=existing_doc,
                is_success=True,
                collection=coll_name
            )
            
    except Exception as e:
        err_msg = f"Failed to merge data into document '{doc_id}' in '{coll_name}' using aggregation: {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(
            db_result=None, 
            is_success=False, 
            errors=[err_msg], 
            collection=coll_name
        )
    finally:
        if task_result and task_result.is_success:
            state = Completed(
                data=task_result, 
                message=f"✅ Merged data into document '{doc_id}' in '{coll_name}' using aggregation"
            )
        else:
            state = Failed(
                data=task_result, 
                message=f"❌ Failed to merge data into document '{doc_id}' in '{coll_name}' using aggregation"
            )
        
        # Create artifact with result summary
        t_r_markdown = generic_results_to_markdown(
            {
                "collection": task_result.collection,
                "document_id": doc_id,
                "operation": "merge_aggregation",
                "is_success": task_result.is_success,
                "errors": task_result.errors if task_result.errors else None
            }
        )
            
        await create_markdown_artifact(
            markdown=t_r_markdown, 
            key=f"db-merge-document-agg-{coll_name}-{doc_id[:8]}",
            description=f"MongoDB document enrichment operation using aggregation for collection: {coll_name}"
        )
        
        return state

@task(name="merge_results")
async def merge_results(
    doc_id: str,
    ai_results: Union[List[AgentAnalysisResult], AgentAnalysisResult],
    coll_name: str,
    db_name: Optional[str] = None,
    array_field: Optional[str] = "files",
    file_path_field: Optional[str] = "path",
) -> DBTaskResult:
    """
    Merge AI analysis results (AgentAnalysisResult objects) into an existing document in MongoDB.
    
    This specialized task handles the complex structure of AgentAnalysisResult objects,
    properly extracting file paths and organizing the analysis data for storage.
    
    Args:
        doc_id: The document ID to enrich (can be string or ObjectId compatible)
        ai_results: One or more AgentAnalysisResult objects containing analysis data
        coll_name: The collection name where the document is stored
        db_name: Optional database name override
        array_field: Name of array field containing file objects (default: 'files')
        file_path_field: Field name in array elements for file path (default: 'path')
        result_field: Field name to store AI results under (default: 'ai_enrichment')
        
    Returns:
        DBTaskResult: The result of the merge operation containing the updated document
    """
    excluded_fields = ['file_path','instructions', 'obj_id', 'repo_name']
    task_result = None
    actual_db_name = db_name or DB_NAME
    
    try:
        if not coll_name:
            raise ValueError("Collection name is required")
        
        if not doc_id:
            raise ValueError("Document ID is required")
            
        if not ai_results:
            raise ValueError("AI results are required")
        
        # Convert single result to list for uniform processing
        results_list = [ai_results] if not isinstance(ai_results, list) else ai_results
        
        # Process results to extract enrichment data
        enrichment_data = {}
        
        for result in results_list:
            file_path = (getattr(result,'file_path', '') or result.get('file_path',''))
            
            # Skip if there's no file_path
            if not file_path:
                logger.warning(f"AI result missing file_path field: {result}")
                continue
            
            # Warn about possible collisions
            if file_path not in enrichment_data:
                enrichment_data[file_path] = {}
            else:
                logger.log_warning_w_trace(f"Collision detected. merge_ai_results tried to recreate enrichment_data, but file_path already in it.\nExisting val: {enrichment_data[file_path]},]")
                continue
            
            # Add all remaining fields to the enrichment data
            for key, value in result.items():
                # Ignore file_path fields
                if key not in excluded_fields:
                    enrichment_data[file_path][key] = value
        
        # Now use the existing merge_documents function with our processed data
        return await db_merge_documents_aggregation(
            doc_id=doc_id,
            enrichment_data=enrichment_data if enrichment_data else {},
            coll_name=coll_name,
            db_name=actual_db_name,
            array_field=array_field,
            array_path_field=file_path_field
        )
        
    except Exception as e:
        err_msg = f"Failed to merge AI results into document '{doc_id}' in '{coll_name}': {str(e)}"
        logger.error(err_msg)
        task_result = DBTaskResult(
            db_result=None, 
            is_success=False, 
            errors=[err_msg], 
            collection=coll_name
        )
        
        state = Failed(
            data=task_result, 
            message=f"❌ Failed to merge AI results into document '{doc_id}' in '{coll_name}'"
        )
        
        # Create artifact with result summary
        t_r_markdown = generic_results_to_markdown(
            {
                "collection": task_result.collection,
                "document_id": doc_id,
                "operation": "merge_ai_results",
                "is_success": task_result.is_success,
                "errors": task_result.errors if task_result.errors else None
            }
        )
            
        await create_markdown_artifact(
            markdown=t_r_markdown, 
            key=f"db-merge-ai-results-{coll_name}-{doc_id[:8]}",
            description=f"MongoDB AI results enrichment operation for collection: {coll_name}"
        )
        
        return state


__all__ = ["store_results", "retrieve_documents", "db_retrieve_document_by_id", "merge_results"]