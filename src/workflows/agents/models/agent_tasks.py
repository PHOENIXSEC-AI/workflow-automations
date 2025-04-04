from typing import Dict, Any, Optional, Type
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


from workflows.agents.models.agent_results import AgentAnalysisResult
from core.models import RepoAnalysisResult

@dataclass
class RunAgentDeps:
    repomix_data: RepoAnalysisResult = field(
        default=None,
        metadata={
            "description": "Repo Analysis Data gathered with Repomix tool"
        }
    )
    result_type: Type[AgentAnalysisResult] = field(
        default_factory=dict,
        metadata={
            "description": "Model Schema of expected Agent result"
        }
    )
    shared_agent: Optional[Any] = field(
        default=None,
        metadata={
            "description": "Shared instance of AI Agent to perform given task"
        }
    )
    

# class RunAITask(BaseModel):
#     """Model representing the task context for AI analysis."""
#     db_name: str = Field(
#         description="Name of the MongoDB database"
#     )
#     db_col_name: str = Field(
#         description="Name of the MongoDB collection"
#     )
#     target_obj_id: str = Field(
#         description="ID of the target object being analyzed"
#     )
#     flow_id: str = Field(
#         description="ID of the Prefect flow"
#     )
#     flow_name: str = Field(
#         description="Name of the Prefect flow"
#     )
#     flow_run_name: str = Field(
#         description="Name of the specific flow run"
#     )
#     flow_run_count: int = Field(
#         description="Count of flow runs"
#     )
#     task_run_id: str = Field(
#         description="ID of the specific task run"
#     )
#     task_run_name: str = Field(
#         description="Name of the specific task run"
#     )





__all__ = ["RunAgentDeps"]