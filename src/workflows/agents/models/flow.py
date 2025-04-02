from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

@dataclass
class RunAIDeps:
    db_name: str = field(
        default='workflows',
        metadata={
            "description": "Name of the MongoDB database where code analysis data is stored. Default is 'workflows'."
        })
    
    db_col_name: str = field(
        default='repomix',
        metadata={
            "description": "Name of the MongoDB collection within the database where code repository information is stored. Default is 'repomix'."
        }
    )
    
    target_obj_id: str = field(
        default=...,
        metadata={
            "description": "Unique identifier for the specific code file or component being analyzed. This ID corresponds to a document in the MongoDB collection that contains the code content and metadata."
        })
    
    # Use Any type for runtime to avoid circular imports
    shared_agent: Optional[Any] = field(
        default=None,
        metadata={
            "description": "Shared instance of AI Agent to perform given task"
        }
    )
    def to_dict(self) -> Dict[str, str]:
        """
        Convert the RunAIDeps instance to a dictionary.
        
        Returns:
            A dictionary representation of the model, excluding the shared_agent field.
        """
        return {
            "db_name": self.db_name,
            "db_col_name": self.db_col_name,
            "target_obj_id": self.target_obj_id
        }
    
    def __dict__(self) -> Dict[str, str]:
        """
        Override __dict__ to provide a simplified dictionary representation.
        
        Returns:
            A dictionary representation of the model, excluding the shared_agent field.
        """
        return self.to_dict()
    
    def __json__(self) -> Dict[str, str]:
        """
        Make the class JSON serializable by supporting __json__ method.
        
        Returns:
            A dictionary representation of the model, excluding the shared_agent field.
        """
        return self.to_dict()
    
    def toJSON(self) -> Dict[str, str]:
        """
        Provide a common method name for JSON serialization.
        
        Returns:
            A dictionary representation of the model, excluding the shared_agent field.
        """
        return self.to_dict()

class RunAITask(BaseModel):
    """Model representing the task context for AI analysis."""
    db_name: str = Field(
        description="Name of the MongoDB database"
    )
    db_col_name: str = Field(
        description="Name of the MongoDB collection"
    )
    target_obj_id: str = Field(
        description="ID of the target object being analyzed"
    )
    flow_id: str = Field(
        description="ID of the Prefect flow"
    )
    flow_name: str = Field(
        description="Name of the Prefect flow"
    )
    flow_run_name: str = Field(
        description="Name of the specific flow run"
    )
    flow_run_count: int = Field(
        description="Count of flow runs"
    )
    task_run_id: str = Field(
        description="ID of the specific task run"
    )
    task_run_name: str = Field(
        description="Name of the specific task run"
    )

__all__ = ["RunAIDeps","RunAITask"]