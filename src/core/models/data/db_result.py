"""
Database operation result models.
"""
from typing import Any, Optional

from .task_result import TaskResult

class DBResult(TaskResult[Any]):
    """
    Result of a database operation.
    
    This extends the base TaskResult to include database-specific information.
    """
    collection: str = ""
    document_id: Optional[str] = None
    document_count: int = 0
    
    def set_document_id(self, doc_id: str) -> 'DBResult':
        """Set the document ID from a successful insert operation."""
        self.document_id = str(doc_id)
        self.result = str(doc_id)
        return self
    
    def set_document_count(self, count: int) -> 'DBResult':
        """Set the document count from a successful query operation."""
        self.document_count = count
        return self 