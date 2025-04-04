from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Self, Tuple

from core.config import app_config
from core.utils import LoggerFactory
from core.models.data.db import BaseDocument

from .async_storage import AsyncWorkflowStorage

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseDocument)

logger = LoggerFactory.get_logger(name=app_config.APP_TITLE,log_level=app_config.log_level, trace_enabled=True)

class AsyncRepository(Generic[T]):
    """
    Generic async repository for working with Pydantic models.
    
    This repository provides an asynchronous interface for CRUD operations
    on Pydantic models stored in AIOTinyDB.
    """
    
    def __init__(self, model_class: Type[T], storage: AsyncWorkflowStorage, table_name: Optional[str] = None):
        """
        Initialize the repository.
        
        Args:
            model_class: The Pydantic model class.
            storage: The async storage instance. If None, creates new instance of AsyncWorkflowStorage
            table_name: The name of the table. If None, uses the model class name.
        """
        self.storage = storage
        self.model_class = model_class
        self.table_name = table_name or model_class.__name__
    
    async def create(self, model: T) -> Tuple[str,str]:
        """
        Create a new document from a model.
        
        Args:model_class
            model: The model instance to create.
            
        Returns:
            The ID of the created document.
        """
        assert all([self.storage,self.table_name, model]), "Expected valid values for self.storage, self.table_name, model"
        
        data = {}
        doc_id = ""
        err_msg = ""
        
        if isinstance(model,dict):
            data = model
        elif getattr(model,'model_dump'):
            data = model.model_dump()
        elif getattr(model,'to_dict'):
            data = model.to_dict()
        else:
            err_msg = f"Invalid object type provided to {Self.__name__}.create(). Expected a Pydantic BaseModel, dictionary, or an object with a to_dict() method, but received {type(model).__name__}."
            logger.error(err_msg)
        
        if not err_msg:
            async with self.storage:
                doc_id = await self.storage.insert(self.table_name, data)
        
        return doc_id, err_msg
    
    async def create_many(self, models: List[T]) -> List[str]:
        """
        Create multiple documents from models.
        
        Args:
            models: The list of model instances to create.
            
        Returns:
            The list of created document IDs.
        """
        data_list = [model.to_dict() for model in models]
        doc_ids = await self.storage.insert_multiple(self.table_name, data_list)
        return doc_ids
    
    async def get_all(self) -> List[T]:
        """
        Get all documents as models.
        
        Returns:
            A list of model instances.
        """
        docs = await self.storage.get_all(self.table_name)
        return [self.model_class(**doc) for doc in docs]
    
    async def get_by_id(self, doc_id: str) -> Optional[T]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: The document ID.
            
        Returns:
            The model instance if found, None otherwise.
        """
        doc = await self.storage.get_by_id(self.table_name, doc_id)
        if doc is None:
            return None
        return self.model_class(**doc)
    
    async def find(self, query) -> List[T]:
        """
        Find documents using a TinyDB query.
        
        Args:
            query: The TinyDB query to execute.
            
        Returns:
            A list of model instances matching the query.
        """
        docs = await self.storage.query(self.table_name, query)
        return [self.model_class(**doc) for doc in docs]
    
    async def find_one(self, query) -> Optional[T]:
        """
        Find a single document using a TinyDB query.
        
        Args:
            query: The TinyDB query to execute.
            
        Returns:
            A model instance if found, None otherwise.
        """
        docs = await self.storage.query(self.table_name, query)
        if not docs:
            return None
        return self.model_class(**docs[0])
    
    async def update(self, doc_id: str, model: T) -> bool:
        """
        Update a document with a model.
        
        Args:
            doc_id: The document ID.
            model: The model instance with updated data.
            
        Returns:
            True if the document was updated, False otherwise.
        """
        if hasattr(model,'model_dump'):
            data = model.model_dump()
        elif hasattr(model,'to_dict'):
            data = model.to_dict()
        elif isinstance(model,dict):
            data = model
        else:
            raise ValueError(f"DB update received unsupported data type: {type(model).__name__}")
        
        async with self.storage:
            db_update_result = await self.storage.update(self.table_name, doc_id, data)
        
        return db_update_result
    
    async def delete(self, doc_id: str) -> bool:
        """
        Delete a document by its ID.
        
        Args:
            doc_id: The document ID.
            
        Returns:
            True if the document was deleted, False otherwise.
        """
        return await self.storage.delete(self.table_name, doc_id)
    
    async def count(self, query=None) -> int:
        """
        Count documents.
        
        Args:
            query: Optional TinyDB query to filter documents.
            
        Returns:
            The number of documents matching the query, or total count if query is None.
        """
        return await self.storage.count(self.table_name, query)
    
    async def update_document_with_merged_data(self, doc_id, org_result_data):
        """
        Update the document in storage with merged data.
        
        Args:
            doc_id: Document ID to update
            org_result_data: Merged result data to save memory
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if not doc_id:
            logger.warning("No document ID provided for update")
            return False
            
        update_success = await self.update(doc_id, org_result_data)
        
        if not update_success:
            logger.warning(f"Failed to update document with merged strategy results")
        else:
            logger.info(f"Successfully updated document with merged strategy results")
            
        return update_success
