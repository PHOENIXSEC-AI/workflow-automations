"""
Common task result models.
"""
from typing import Any, List, Optional, Dict, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class TaskResult(BaseModel, Generic[T]):
    """
    Base class for task operation results.
    
    This provides a standardized structure for task results across the application.
    """
    result: Optional[T] = None
    is_success: bool = False
    errors: List[str] = Field(default_factory=list)
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_error(self, error: str) -> 'TaskResult[T]':
        """Add an error message to the result."""
        self.errors.append(error)
        self.is_success = False
        return self
    
    def add_metadata(self, key: str, value: Any) -> 'TaskResult[T]':
        """Add metadata to the result."""
        self.metadata[key] = value
        return self
    
    def set_result(self, result: T, message: str = "") -> 'TaskResult[T]':
        """Set the result value and mark as successful."""
        self.result = result
        self.is_success = True
        if message:
            self.message = message
        return self 