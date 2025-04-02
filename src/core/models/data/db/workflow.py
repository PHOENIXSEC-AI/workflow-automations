from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from .base import BaseDocument


class WorkflowStatus(str, Enum):
    """Workflow status enum"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskDefinition(BaseModel):
    """Task definition model"""
    name: str
    description: Optional[str] = None
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    timeout: Optional[int] = None  # in seconds


class WorkflowDefinition(BaseDocument):
    """Workflow definition model"""
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    tasks: List[TaskDefinition] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None
    
    
class TaskExecution(BaseDocument):
    """Task execution model"""
    workflow_run_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    

class WorkflowExecution(BaseDocument):
    """Workflow execution model"""
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    tasks: List[TaskExecution] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None 