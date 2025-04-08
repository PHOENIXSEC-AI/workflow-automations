"""
Models for extracting and structuring analysis data from agent results.

This module defines a structured hierarchy of Pydantic models used to capture
and represent data extracted by `env-vars-extractor`, including environment variables,
database information, and API endpoints.
"""
from typing import List, Self
from pydantic import BaseModel, Field

from .base import AgentAnalysisResult

# Environmental Variables
class EnvVarInfo(BaseModel):
    """
    Information about an environment variable detected in the codebase.
    
    Captures details about environment variables, including their purpose
    and where they're defined or used.
    """
    name: str = Field(description="Name of the environment variable")
    description: str = Field(description="Purpose and usage of this variable")
    context: str = Field(description="Additional context like where it's defined or used")

# Database Tables
class DbTable(BaseModel):
    """
    Information about a database table detected in the codebase.
    
    Captures details about database tables, including the operations
    performed on them and how they're used in the application.
    """
    name: str = Field(description="Name of the database table")
    operations: List[str] = Field(description="Operations performed on this table (read, write, etc)")
    context: str = Field(description="How this table is used")

# Database Information
class DbInfo(BaseModel):
    """
    Information about a database detected in the codebase.
    
    Captures details about databases including their tables
    and overall usage context.
    """
    name: str = Field(description="Name of the database")
    tables: List[DbTable] = Field(default_factory=list, description="Tables in this database")
    context: str = Field(description="Overall database usage context")

# API Endpoints
class ApiEndpoint(BaseModel):
    """
    Information about an API endpoint detected in the codebase.
    
    Captures details about API endpoints including their purpose
    and implementation details.
    """
    name: str = Field(description="Name of the endpoint")
    description: str = Field(description="What this endpoint does")
    context: str = Field(description="Implementation details or usage notes")

# API Information
class ApiInfo(BaseModel):
    """
    Information about an API group detected in the codebase.
    
    Captures details about groups of related API endpoints including
    the base host and general description.
    """
    host: str = Field(description="API endpoint base path")
    context: str = Field(description="General description of this API group")
    endpoints: List[ApiEndpoint] = Field(default_factory=list, description="Endpoints in this API")

# Concrete BaseAgentAnalysisResult with expected fields
class BaseAgentAnalysisResult(AgentAnalysisResult):
    """
    Structured result from agent analysis with specific expected fields.
    
    Extends the base AgentAnalysisResult to include structured data about
    environment variables, databases, and APIs detected in the analyzed code.
    """
    env_vars: List[EnvVarInfo] = Field(default_factory=list, description="Environment variables detected")
    db: List[DbInfo] = Field(default_factory=list, description="Database information detected")
    api: List[ApiInfo] = Field(default_factory=list, description="API endpoints detected")
    
    @staticmethod
    def default() -> Self:
        """
        Creates a default instance with default values.
        
        Returns:
            A new BaseAgentAnalysisResult instance with default values
        """
        return BaseAgentAnalysisResult(file_path='default')

__all__ = [
    "EnvVarInfo", 
    "DbTable", 
    "DbInfo", 
    "ApiEndpoint", 
    "ApiInfo", 
    "BaseAgentAnalysisResult"
]