from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple, Any, Self


class FileRank(BaseModel):
    """Represents a ranked file in the repository."""
    rank: int = Field(..., description="Numerical ranking of the file")
    path: str = Field(..., description="Path to the file relative to repository root")
    chars: int = Field(..., description="Number of characters in the file")
    tokens: int = Field(..., description="Number of tokens in the file")


class Summary(BaseModel):
    """Represents the repository summary statistics."""
    total_files: int = Field(..., description="Total number of files in the repository")
    total_chars: int = Field(..., description="Total number of characters across all files")
    total_tokens: int = Field(..., description="Total number of tokens across all files")
    output_file: str = Field(..., description="Path to the generated output file")
    security: str = Field(
        ...,
        description="Security check result, typically a checkmark followed by a message"
    )


class ToolOutput(BaseModel):
    """Represents the tool output section of the result data."""
    top_files: List[FileRank] = Field(
        ...,
        description="List of top files by size, ranked from largest to smallest"
    )
    summary: Summary = Field(..., description="Summary statistics for the repository")


class RepoFile(BaseModel):
    """Represents a file in the repository with its content."""
    path: str = Field(..., description="Path to the file relative to repository root")
    content: str = Field(
        ...,
        description="Content of the file, often with line numbers prefixed to each line"
    )
    # Allow arbitrary additional fields
    model_config = {
        "extra": "allow",
    }


class RepomixResultData(BaseModel):
    """Root model representing the complete result data from repository analysis."""
    directory_structure: str = Field(
        ...,
        description="ASCII representation of the repository directory structure"
    )
    instruction: Optional[str] = Field(
        None,
        description="The instruction/template used for generating the repository analysis"
    )
    tool_output: ToolOutput = Field(
        ...,
        description="Output from the tool that analyzed the repository"
    )
    files: List[RepoFile] = Field(
        ...,
        description="List of all files in the repository with their content"
    )
    
    # Allow arbitrary additional fields
    model_config = {
        "extra": "allow",
    }
    
    @classmethod
    def from_json_file(cls, file_path: str) -> "RepomixResultData":
        """
        Load ResultData from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            ResultData instance
        """
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.model_validate(data)
    
    
    def to_json_string(self) -> str:
        """
        Serialize the ResultData object to a JSON string.
        
        Returns:
            A JSON string representation of the ResultData object
        """
        return self.model_dump_json(indent=2)
    
    def get_file_by_path(self, path: str) -> Optional[RepoFile]:
        """
        Get a file by its path.
        
        Args:
            path: Path to the file
            
        Returns:
            RepoFile instance if found, None otherwise
        """
        for file in self.files:
            if file.path == path:
                return file
        return None
    
    def get_files_by_extension(self, extension: str) -> List[RepoFile]:
        """
        Get all files with a specific extension.
        
        Args:
            extension: File extension (e.g., 'py', 'md')
            
        Returns:
            List of RepoFile instances
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
            
        return [file for file in self.files if file.path.endswith(extension)]
    
    def get_file_statistics_by_extension(self) -> Dict[str, Tuple[int, int, int]]:
        """
        Get statistics (file count, total chars, total tokens) grouped by file extension.
        
        Returns:
            Dictionary mapping extensions to (count, chars, tokens) tuples
        """
        stats = {}
        
        for file in self.files:
            # Extract extension (empty string if no extension)
            parts = file.path.split('.')
            ext = parts[-1] if len(parts) > 1 else ''
            
            if ext not in stats:
                stats[ext] = [0, 0, 0]  # count, chars, tokens
                
            # Find the corresponding FileRank to get char and token counts
            file_rank = next((f for f in self.tool_output.top_files if f.path == file.path), None)
            
            if file_rank:
                stats[ext][0] += 1
                stats[ext][1] += file_rank.chars
                stats[ext][2] += file_rank.tokens
        
        # Convert lists to tuples
        return {ext: tuple(values) for ext, values in stats.items()}


class RepoAnalysisResult(BaseModel):
    """Standardized repository result model."""
    
    repository_url: str = Field(..., description="The URL of the repository")
    status: str = Field(default="failed", description="The status of the processing (success/failed)")
    error: Optional[str] = Field(default=None, description="Optional error message if status is failed")
    result: Optional[RepomixResultData] = Field(default=None, description="Optional result data if status is success")
    result_path: Optional[str] = Field(default=None, description="Optional local path of the repository analysis document")
    
    class Config:
        # schema_extra = {
        #     "example": {
        #         "repository_url": "https://github.com/user/repo",
        #         "status": "success",
        #         "error": None,
        #         "result": {"key": "value"},
        #         "result_path": "/tmp/...",
        #     }
        # }
        json_schema_extra = {
            "example": {
                "repository_url": "https://github.com/user/repo",
                "status": "success",
                "error": None,
                "result": {"key": "value"},
                "result_path": "/tmp/...",
            }
        }
        

__all__ = ["RepomixResultData", "RepoFile", "ToolOutput", "Summary", "FileRank", "RepoAnalysisResult"] 