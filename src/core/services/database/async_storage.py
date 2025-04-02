import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from aiotinydb import AIOTinyDB

# Type variable for Pydantic models
T = TypeVar('T')

from core.config import app_config
from core.utils import LoggerFactory

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

class AsyncWorkflowStorage:
    """
    Async storage class using AIOTinyDB for concurrent operations.
    
    This class provides an asynchronous interface for CRUD operations on workflow data.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the storage with the given database path.
        
        Args:
            db_path: The path to the database file. If None, uses a default path.
        """
        if db_path is None:
            # Default to a directory within the user's home directory
            home_dir = os.path.expanduser("~")
            db_dir = os.path.join(home_dir, app_config.DB_DATA_DIR)
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, app_config.DB_DATA_FILENAME)
        
        self.db_path = db_path
        self.db = None
        self._db_context = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        # try Create the AIOTinyDB context manager and enter it
        try:
            self._db_context = AIOTinyDB(self.db_path)
            self.db = await self._db_context.__aenter__()
        except Exception as ex:
            err_msg = f"Error: Failed to initialize AIOTinyDB context: {str(ex)}"
            logger.error(err_msg)
        finally:
            return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        try:
            await self._db_context.__aexit__(exc_type, exc_val, exc_tb)
            self.db = None
            self._db_context = None
        except Exception as ex:
            err_msg = f"Error: Failed to deconstruct AIOTinyDB context: {str(ex)}"
            logger.error(err_msg)
    
    async def get_table(self, table_name: str):
        """
        Get a table by name.
        
        Args:
            table_name: The name of the table.
            
        Returns:
            The table instance.
        """
        table = None
        
        try:
            table = self.db.table(table_name)
        except RuntimeError as run_err:
            err_msg = f"Error: {str(run_err)}. Make sure DB is opened correctly. Use 'async with AsyncWorkflowStorage():'"
            logger.error(err_msg)
        except Exception as ex:
            err_msg = f"Error: Uncaught Exception Occured: {str(ex)}"
            logger.error(err_msg)
        finally:
            return table
    
    async def insert(self, table_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into a table.
        
        Args:
            table_name: The name of the table.
            data: The data to insert.
            
        Returns:
            The ID of the inserted document.
        """
        table = await self.get_table(table_name)
        doc_id = table.insert(data)
        return str(doc_id)
    
    async def insert_multiple(self, table_name: str, data_list: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents into a table.
        
        Args:
            table_name: The name of the table.
            data_list: The list of documents to insert.
            
        Returns:
            The list of inserted document IDs.
        """
        table = await self.get_table(table_name)
        doc_ids = table.insert_multiple(data_list)
        return [str(doc_id) for doc_id in doc_ids]
    
    async def get_all(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get all documents from a table.
        
        Args:
            table_name: The name of the table.
            
        Returns:
            A list of all documents in the table.
        """
        table = await self.get_table(table_name)
        return table.all()
    
    async def get_by_id(self, table_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            table_name: The name of the table.
            doc_id: The document ID.
            
        Returns:
            The document if found, None otherwise.
        """
        table = await self.get_table(table_name)
        doc = table.get(doc_id=int(doc_id))
        return doc
    
    async def update(self, table_name: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a document by its ID.
        
        Args:
            table_name: The name of the table.
            doc_id: The document ID.
            data: The new data to update.
            
        Returns:
            True if the document was updated, False otherwise.
        """
        table = await self.get_table(table_name)
        return bool(table.update(data, doc_ids=[int(doc_id)]))
    
    async def delete(self, table_name: str, doc_id: str) -> bool:
        """
        Delete a document by its ID.
        
        Args:
            table_name: The name of the table.
            doc_id: The document ID.
            
        Returns:
            True if the document was deleted, False otherwise.
        """
        table = await self.get_table(table_name)
        return bool(table.remove(doc_ids=[int(doc_id)]))
    
    async def query(self, table_name: str, query):
        """
        Query documents in a table using TinyDB Query.
        
        Args:
            table_name: The name of the table.
            query: The TinyDB query to execute.
            
        Returns:
            A list of documents matching the query.
        """
        table = await self.get_table(table_name)
        return table.search(query)


