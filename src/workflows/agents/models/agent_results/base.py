from typing import Self
from pydantic import BaseModel, Field, model_validator

class AgentAnalysisResult(BaseModel):
    """
    Model for specific analysis result content.
    
    Base class for agent analysis results with a required file_path field
    and support for arbitrary additional attributes.
    """
    file_path: str = Field(
        default_factory='',
        description="Filename of analysed file"
    )
    
    # Allow arbitrary additional fields
    model_config = {
        "extra": "allow",
    }
    
    @model_validator(mode='after')
    def validate_file_path(self) -> 'AgentAnalysisResult':
        """
        Validates that the file_path is provided.
        
        Raises:
            ValueError: If file_path is empty or not provided
            
        Returns:
            The validated model instance
        """
        if not self.file_path:
            raise ValueError("file_path is required")
        return self
    
    @staticmethod
    def default() -> Self:
        """
        Creates a default instance with a default file path.
        
        Returns:
            A new AgentAnalysisResult instance with default values
        """
        return AgentAnalysisResult(file_path='default')
    
    @staticmethod
    def create_error_result(error_message: str, limitations: str = "", file_path:str='default') -> Self:
        """
        Create a structured AskAgentResult for error conditions.
        
        Args:
            error_message: The error message to include
            limitations: Optional description of limitations that caused the error
            file_path: The file path to associate with this error result
            
        Returns:
            A validated AskAgentResult model with error information
        """
        result_data = {
            "file_path": file_path,
            "limitations": limitations or error_message,
            "errors": error_message
        }
        
        return AgentAnalysisResult.model_validate(result_data)