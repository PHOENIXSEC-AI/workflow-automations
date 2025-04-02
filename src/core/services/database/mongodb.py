import os
import io
import sys
import signal
import gridfs
import time

from datetime import datetime, timezone
from bson.objectid import ObjectId

from typing import List, Dict, Any, Tuple, Optional, Union
from contextlib import contextmanager
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne, InsertOne
from pymongo.errors import ConnectionFailure, OperationFailure, BulkWriteError
from pymongo.collection import Collection
from pymongo.database import Database

from core.config import app_config
from core.utils import LoggerFactory

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)
class MongoDBConnector:
    def __init__(self, connection_string:str, database:str='threat_intel'):
        """
        Initializes a MongoDB connection with robust error handling.

        :param logger: Optional logger instance for logging. If not provided, a default logger will be used.
        :param database: The name of the database to connect to.
        """
        self.logger = logger
        self.mongo_uri = connection_string
        self.db_name = database
        self._gridfs = None

        try:
            # Ensure MONGO_URI is set
            if not self.mongo_uri:
                self.logger.error("connection_string is required.")
                raise ConnectionFailure("connection_string is required.")

            # Attempt to create the MongoDB client and connect
            self.client = MongoClient(self.mongo_uri)

            # Verify the connection and authentication
            self.db = self.client[database]
            self.logger.debug(f"Checking database authentication for: {database}")
            self.db.list_collection_names()  # Forces authentication and connection check

            self.logger.debug(f"Successfully connected to MongoDB database: {self.db.name}")
        
        except ConnectionFailure as conn_err:
            self.logger.error(f"Connection failure while connecting to MongoDB: {conn_err}")
            raise conn_err
        except OperationFailure as op_err:
            self.logger.error(f"Operation failure in MongoDB: {op_err}")
            raise op_err
        except Exception as ex:
            self.logger.error(f"Unexpected error occurred while connecting to MongoDB: {ex}")
            raise
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)  # Handle CTRL+C
        signal.signal(signal.SIGTERM, self._signal_handler)  # Handle termination signal
    
    @property
    def gridfs(self) -> gridfs.GridFS:
        """
        Get a GridFS instance for storing large files.
        
        Returns:
            GridFS instance connected to the current database
        """
        if self._gridfs is None:
            self._gridfs = gridfs.GridFS(self.db)
        return self._gridfs
    
    def initialize_gridfs(self) -> bool:
        """
        Explicitly initialize GridFS and test the connection.
        
        Returns:
            True if GridFS was initialized successfully, False otherwise
        """
        try:
            self.logger.info(f"Explicitly initializing GridFS for database {self.db_name}")
            self._gridfs = gridfs.GridFS(self.db)
            
            # Test the GridFS connection by listing a file (limit 1)
            list(self._gridfs.find().limit(1))
            
            self.logger.info("GridFS initialized and tested successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize GridFS: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self._gridfs = None
            return False
            
    def store_file_in_gridfs(self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a file in GridFS.
        
        Args:
            content: The content to store
            filename: Name to associate with the file
            metadata: Additional metadata to store with the file
            
        Returns:
            The GridFS file ID
        """
        try:
            if not hasattr(self, '_gridfs'):
                self._gridfs = gridfs.GridFS(self.db)
            
            # Extract key metadata for logging
            content_size = len(content)
            chunk_index = metadata.get('chunk_index', 0) if metadata else 0
            total_chunks = metadata.get('total_chunks', 1) if metadata else 1
            token_count = metadata.get('token_count', 0) if metadata else 0
            chunk_token_count = metadata.get('chunk_token_count', token_count) if metadata else 0
            
            # Log before storage attempt
            if total_chunks > 1:
                self.logger.debug(f"Storing chunk {chunk_index+1}/{total_chunks} of file '{filename}' in GridFS: {content_size} bytes, {chunk_token_count} tokens")
            else:
                self.logger.debug(f"Storing file '{filename}' in GridFS: {content_size} bytes, {token_count} tokens")
            
            # Add timestamp if not in metadata
            if metadata is None:
                metadata = {}
            if 'created_at' not in metadata:
                metadata['created_at'] = datetime.now(tz=timezone.utc)
                
            # Record performance metrics
            start_time = time.time()
            
            # Store the file
            file_id = str(self._gridfs.put(
                content.encode('utf-8'),
                filename=filename,
                metadata=metadata
            ))
            
            elapsed_time = time.time() - start_time
            
            # Log success with performance data
            if total_chunks > 1:
                self.logger.debug(f"Stored chunk {chunk_index+1}/{total_chunks} of '{filename}' in GridFS: ID={file_id}, Size={content_size} bytes, Time={elapsed_time:.3f}s")
            else:
                self.logger.debug(f"Stored file '{filename}' in GridFS: ID={file_id}, Size={content_size} bytes, Time={elapsed_time:.3f}s")
            
            return file_id
        except Exception as e:
            self.logger.error(f"Failed to store file '{filename}' in GridFS: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    def retrieve_file_from_gridfs(self, file_id: str) -> str:
        """
        Retrieve a file from GridFS by ID.
        
        Args:
            file_id: ID of the file to retrieve
            
        Returns:
            The file content as a string
        """
        try:
            if not hasattr(self, '_gridfs'):
                self._gridfs = gridfs.GridFS(self.db)
                
            # Convert string ID to ObjectId if needed
            if isinstance(file_id, str):
                from bson.objectid import ObjectId
                file_id = ObjectId(file_id)
                
            start_time = time.time()
            
            # Get the file from GridFS
            grid_out = self._gridfs.get(file_id)
            
            # Get file metadata for logging
            filename = grid_out.filename
            metadata = grid_out.metadata or {}
            chunk_index = metadata.get('chunk_index', 0)
            total_chunks = metadata.get('total_chunks', 1)
            
            # Read file content
            content = grid_out.read()
            content_str = content.decode('utf-8')
            content_size = len(content_str)
            
            elapsed_time = time.time() - start_time
            
            # Log retrieval details
            if total_chunks > 1:
                self.logger.debug(f"Retrieved chunk {chunk_index+1}/{total_chunks} of '{filename}' from GridFS: ID={file_id}, Size={content_size} bytes, Time={elapsed_time:.3f}s")
            else:
                self.logger.debug(f"Retrieved file '{filename}' from GridFS: ID={file_id}, Size={content_size} bytes, Time={elapsed_time:.3f}s")
                
            return content_str
        except Exception as e:
            self.logger.error(f"Failed to retrieve file with ID {file_id} from GridFS: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def list_gridfs_files(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List files in GridFS matching a query.
        
        Args:
            query: MongoDB query to filter files
            
        Returns:
            List of file metadata
        """
        query = query or {}
        files = self.gridfs.find(query)
        
        result = []
        for file in files:
            # Extract relevant metadata
            metadata = {
                'file_id': str(file._id),
                'filename': file.filename,
                'length': file.length,
                'upload_date': file.upload_date,
                'content_type': getattr(file, 'content_type', None)
            }
            
            # Add any custom metadata
            for key in file.metadata or {}:
                if key not in metadata:
                    metadata[key] = file.metadata[key]
                    
            result.append(metadata)
            
        return result
            
    def delete_gridfs_file(self, file_id: str) -> bool:
        """
        Delete a file from GridFS.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)
                
            # Check if the file exists
            if not self.gridfs.exists(file_id):
                self.logger.warning(f"File with ID {file_id} does not exist in GridFS")
                return False
                
            # Delete the file
            self.gridfs.delete(file_id)
            self.logger.debug(f"Deleted file with ID {file_id} from GridFS")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete file from GridFS: {e}")
            return False

    def insert_document(self, collection_name, document):
        """Insert a document into a specified collection."""
        collection = self.db[collection_name]
        
        # Log detailed information about the document before insertion
        doc_size = len(str(document))
        doc_id = document.get('_id', 'auto-generated')
        doc_type = document.get('type', 'unknown')
        
        self.logger.info(f"Inserting document into '{collection_name}' collection: ID={doc_id}, Type={doc_type}, Size={doc_size} bytes")
        
        start_time = time.time()
        result = collection.insert_one(document)
        elapsed_time = time.time() - start_time
        
        self.logger.info(f"Inserted document with ID: {result.inserted_id}, Collection: {collection_name}, Time: {elapsed_time:.3f}s")
        return result.inserted_id
    
    def insert_batch_documents(self, collection_name, documents):
        """Insert multiple documents into a specified collection."""
        collection = self.db[collection_name]
        documents_inserted = 0
        
        if not documents:
            self.logger.warning("No documents to insert.")
            return [], documents_inserted
        
        # Log detailed information about the batch
        batch_size = len(documents)
        total_size = sum(len(str(doc)) for doc in documents)
        
        self.logger.info(f"Inserting batch of {batch_size} documents into '{collection_name}', Total Size: {total_size} bytes")
        
        try:
            start_time = time.time()
            result = collection.insert_many(documents)
            elapsed_time = time.time() - start_time
            
            documents_inserted = len(result.inserted_ids)
            avg_time_per_doc = elapsed_time / documents_inserted if documents_inserted > 0 else 0
            
            self.logger.info(
                f"Successfully inserted {documents_inserted}/{batch_size} documents into '{collection_name}'. "
                f"Total Time: {elapsed_time:.3f}s, Avg: {avg_time_per_doc:.5f}s per document"
            )
            
            return result.inserted_ids, documents_inserted
        
        # Handle OP Errors more gracefully
        except OperationFailure as op_err:
            if 'nInserted' in op_err.details:
                documents_inserted = op_err.details['nInserted']
                
            self.logger.error(
                f"MongoDB Operation Error during batch insert to '{collection_name}': "
                f"{documents_inserted} documents inserted before failure. "
                f"Error: {op_err.details}"
            )
            
            return [], documents_inserted
        
        except Exception as e:
            self.logger.error(f"Error inserting batch of {batch_size} documents into '{collection_name}': {e}")
            return [], documents_inserted

    def find_document(self, collection_name, query):
        """Find a document in a specified collection."""
        collection = self.db[collection_name]
        document = collection.find_one(query)
        self.logger.debug(f"Found document: {document}")
        return document

    def update_document(self, collection_name, query, update, operator='$set'):
        """Update a document in a specified collection."""
        collection = self.db[collection_name]
        
        # Use the specified operator for the update
        if operator == '$addToSet':
            result = collection.update_one(query, {operator: update})
        else:
            result = collection.update_one(query, {'$set': update})
        
        self.logger.debug(f"Updated {result.modified_count} document(s)")
        return result.modified_count

    def delete_document(self, collection_name, query):
        """Delete a document from a specified collection."""
        collection = self.db[collection_name]
        result = collection.delete_one(query)
        self.logger.debug(f"Deleted {result.deleted_count} document(s)")
        return result.deleted_count
    
    def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        """
        Delete multiple documents from a collection.
        
        Args:
            collection_name: Name of the collection
            query: Query to find documents to delete
            
        Returns:
            Number of deleted documents
        """
        collection = self.db[collection_name]
        result = collection.delete_many(query)
        self.logger.debug(f"Deleted {result.deleted_count} document(s)")
        return result.deleted_count
    
    def create_index(self, collection_name: str, keys: List[Tuple[str, int]], 
                    unique: bool = False, sparse: bool = False,
                    background: bool = True, name: Optional[str] = None) -> str:
        """
        Create an index on a collection.
        
        Args:
            collection_name: Name of the collection
            keys: List of (field, direction) tuples
            unique: Whether the index should enforce uniqueness
            sparse: Whether the index should be sparse
            background: Whether to create the index in the background
            name: Optional name for the index
            
        Returns:
            Name of the created index
        """
        collection = self.db[collection_name]
        index_name = collection.create_index(
            keys, 
            unique=unique, 
            sparse=sparse, 
            background=background,
            name=name
        )
        self.logger.debug(f"Created index '{index_name}' on collection '{collection_name}'")
        return index_name
        
    def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute an aggregation pipeline.
        
        Args:
            collection_name: Name of the collection
            pipeline: MongoDB aggregation pipeline
            
        Returns:
            List of aggregation results
        """
        collection = self.db[collection_name]
        results = list(collection.aggregate(pipeline))
        self.logger.debug(f"Aggregation returned {len(results)} results")
        return results
    
    def close(self):
        """Close the MongoDB connection."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed.")
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        self.logger.debug(f"Received signal {sig}, closing connection...")
        self.close()  # Close the connection
        sys.exit(0)  # Exit the program
        
    def __enter__(self):
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()

# Singleton instance of MongoDB connector
_mongodb_connector = None

# Note: Fix imports at the top to include datetime if necessary


def get_mongodb_connector() -> MongoDBConnector:
    """Get or initialize MongoDB connector."""
    
    global _mongodb_connector
    
    if _mongodb_connector is None:
        _mongodb_connector = MongoDBConnector(
            connection_string=app_config.MONGODB_URI,
            database=app_config.MONGODB_DATABASE
        )
    return _mongodb_connector